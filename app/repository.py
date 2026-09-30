from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import joinedload

from app.models import AuditLog, Recommendation, RecommendationStatus, Setting, SupportTicket, TicketStatus, User
from app.services.utils import normalize_key


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Repository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def upsert_user(self, telegram_id: int, username: str | None, full_name: str) -> User:
        async with self.session_factory() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                user = User(telegram_id=telegram_id, username=username, full_name=full_name)
                session.add(user)
            else:
                user.username = username
                user.full_name = full_name
                user.last_seen_at = utcnow()
            await session.commit()
            await session.refresh(user)
            return user

    async def get_user_by_tg(self, telegram_id: int) -> User | None:
        async with self.session_factory() as session:
            return await session.scalar(select(User).where(User.telegram_id == telegram_id))

    async def get_user_by_id(self, user_id: int) -> User | None:
        async with self.session_factory() as session:
            return await session.get(User, user_id)

    async def create_recommendation(self, user_id: int, title: str, author: str, review: str, photo_file_id: str | None, normalized_key: str, duplicate_of_id: int | None) -> Recommendation:
        async with self.session_factory() as session:
            row = Recommendation(user_id=user_id, title=title, author=author, review=review, photo_file_id=photo_file_id, normalized_key=normalized_key, duplicate_of_id=duplicate_of_id)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def find_duplicate(self, normalized_key: str, exclude_id: int | None = None) -> Recommendation | None:
        async with self.session_factory() as session:
            query = select(Recommendation).where(
                Recommendation.normalized_key == normalized_key,
                Recommendation.status.in_([RecommendationStatus.PENDING.value, RecommendationStatus.PUBLISHING.value, RecommendationStatus.PUBLISHED.value]),
            ).order_by(Recommendation.id.desc())
            if exclude_id:
                query = query.where(Recommendation.id != exclude_id)
            return await session.scalar(query)

    async def get_recommendation(self, rec_id: int) -> Recommendation | None:
        async with self.session_factory() as session:
            return await session.scalar(select(Recommendation).options(joinedload(Recommendation.user)).where(Recommendation.id == rec_id))

    async def list_user_recommendations(self, user_id: int, limit: int = 20) -> list[Recommendation]:
        async with self.session_factory() as session:
            return list((await session.scalars(select(Recommendation).where(Recommendation.user_id == user_id).order_by(Recommendation.id.desc()).limit(limit))).all())

    async def pending_with_users(self, limit: int = 15) -> list[tuple[Recommendation, User]]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Recommendation, User)
                .join(User, User.id == Recommendation.user_id)
                .where(Recommendation.status == RecommendationStatus.PENDING.value)
                .order_by(Recommendation.id.asc())
                .limit(limit)
            )
            return list(result.all())

    async def claim_publish(self, rec_id: int) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(
                update(Recommendation)
                .where(and_(Recommendation.id == rec_id, Recommendation.status == RecommendationStatus.PENDING.value))
                .values(status=RecommendationStatus.PUBLISHING.value, updated_at=utcnow())
            )
            await session.commit()
            return result.rowcount == 1

    async def mark_published(self, rec_id: int, message_id: int) -> None:
        async with self.session_factory() as session:
            row = await session.get(Recommendation, rec_id)
            if row:
                row.status = RecommendationStatus.PUBLISHED.value
                row.channel_message_id = message_id
                row.updated_at = utcnow()
                await session.commit()

    async def release_publish(self, rec_id: int) -> None:
        async with self.session_factory() as session:
            await session.execute(
                update(Recommendation)
                .where(and_(Recommendation.id == rec_id, Recommendation.status == RecommendationStatus.PUBLISHING.value))
                .values(status=RecommendationStatus.PENDING.value, updated_at=utcnow())
            )
            await session.commit()

    async def reject(self, rec_id: int, reason: str) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(
                update(Recommendation)
                .where(and_(Recommendation.id == rec_id, Recommendation.status.in_([RecommendationStatus.PENDING.value, RecommendationStatus.PUBLISHING.value])))
                .values(status=RecommendationStatus.REJECTED.value, rejection_reason=reason, updated_at=utcnow())
            )
            await session.commit()
            return result.rowcount == 1

    async def edit_recommendation(self, rec_id: int, **fields: str) -> Recommendation | None:
        async with self.session_factory() as session:
            row = await session.get(Recommendation, rec_id)
            if not row:
                return None
            for field, value in fields.items():
                if hasattr(row, field) and value is not None:
                    setattr(row, field, value)
            row.normalized_key = normalize_key(row.title, row.author)
            row.updated_at = utcnow()
            await session.commit()
            await session.refresh(row)
            return row

    async def stale_publishing(self, minutes: int = 15) -> list[Recommendation]:
        threshold = utcnow() - timedelta(minutes=minutes)
        async with self.session_factory() as session:
            return list((await session.scalars(select(Recommendation).where(and_(Recommendation.status == RecommendationStatus.PUBLISHING.value, Recommendation.updated_at < threshold)))).all())

    async def reset_stale_publishing(self, minutes: int = 15) -> int:
        threshold = utcnow() - timedelta(minutes=minutes)
        async with self.session_factory() as session:
            result = await session.execute(
                update(Recommendation)
                .where(and_(Recommendation.status == RecommendationStatus.PUBLISHING.value, Recommendation.updated_at < threshold))
                .values(status=RecommendationStatus.PENDING.value, updated_at=utcnow())
            )
            await session.commit()
            return int(result.rowcount or 0)

    async def set_setting(self, key: str, value: str) -> None:
        async with self.session_factory() as session:
            row = await session.get(Setting, key)
            if row is None:
                session.add(Setting(key=key, value=value))
            else:
                row.value = value
            await session.commit()

    async def get_setting(self, key: str, default: str | None = None) -> str | None:
        async with self.session_factory() as session:
            row = await session.get(Setting, key)
            return row.value if row else default

    async def settings(self) -> dict[str, str]:
        async with self.session_factory() as session:
            rows = list((await session.scalars(select(Setting))).all())
            return {row.key: row.value for row in rows}

    async def create_support(self, user_id: int, text: str) -> SupportTicket:
        async with self.session_factory() as session:
            row = SupportTicket(user_id=user_id, message_text=text)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def get_support(self, ticket_id: int) -> SupportTicket | None:
        async with self.session_factory() as session:
            return await session.scalar(select(SupportTicket).options(joinedload(SupportTicket.user)).where(SupportTicket.id == ticket_id))

    async def open_support_tickets(self, limit: int = 20) -> list[SupportTicket]:
        async with self.session_factory() as session:
            return list((await session.scalars(select(SupportTicket).options(joinedload(SupportTicket.user)).where(SupportTicket.status == TicketStatus.OPEN.value).order_by(SupportTicket.id.asc()).limit(limit))).all())

    async def claim_support(self, ticket_id: int) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(update(SupportTicket).where(and_(SupportTicket.id == ticket_id, SupportTicket.status == TicketStatus.OPEN.value)).values(status=TicketStatus.REPLYING.value))
            await session.commit()
            return result.rowcount == 1

    async def close_support(self, ticket_id: int, admin_id: int, reply: str | None = None) -> bool:
        async with self.session_factory() as session:
            values = {'status': TicketStatus.REPLIED.value, 'replied_by': admin_id, 'replied_at': utcnow()}
            if reply is not None:
                values['admin_reply'] = reply
            result = await session.execute(update(SupportTicket).where(SupportTicket.id == ticket_id).values(**values))
            await session.commit()
            return result.rowcount == 1

    async def search_users(self, query: str, limit: int = 15) -> list[User]:
        q = query.strip()
        async with self.session_factory() as session:
            conditions = [User.username.ilike(f'%{q.lstrip("@")}%', escape='\\'), User.full_name.ilike(f'%{q}%')]
            if q.isdigit():
                conditions.append(User.telegram_id == int(q))
            return list((await session.scalars(select(User).where(or_(*conditions)).order_by(User.id.desc()).limit(limit))).all())

    async def set_blocked(self, user_id: int, blocked: bool) -> None:
        async with self.session_factory() as session:
            row = await session.get(User, user_id)
            if row:
                row.is_blocked = blocked
                await session.commit()

    async def all_user_ids(self) -> list[int]:
        async with self.session_factory() as session:
            return [int(value) for value in (await session.scalars(select(User.telegram_id).where(User.is_blocked.is_(False))).all())]

    async def audit(self, admin_id: int, action: str, target_type: str | None = None, target_id: int | None = None, details: str | None = None) -> None:
        async with self.session_factory() as session:
            session.add(AuditLog(admin_telegram_id=admin_id, action=action, target_type=target_type, target_id=target_id, details=details))
            await session.commit()

    async def stats(self) -> dict[str, int]:
        async with self.session_factory() as session:
            total_users = await session.scalar(select(func.count()).select_from(User)) or 0
            total_recs = await session.scalar(select(func.count()).select_from(Recommendation)) or 0
            pending = await session.scalar(select(func.count()).select_from(Recommendation).where(Recommendation.status == RecommendationStatus.PENDING.value)) or 0
            published = await session.scalar(select(func.count()).select_from(Recommendation).where(Recommendation.status == RecommendationStatus.PUBLISHED.value)) or 0
            rejected = await session.scalar(select(func.count()).select_from(Recommendation).where(Recommendation.status == RecommendationStatus.REJECTED.value)) or 0
            open_support = await session.scalar(select(func.count()).select_from(SupportTicket).where(SupportTicket.status == TicketStatus.OPEN.value)) or 0
            blocked = await session.scalar(select(func.count()).select_from(User).where(User.is_blocked.is_(True))) or 0
            return {'users': int(total_users), 'recommendations': int(total_recs), 'pending': int(pending), 'published': int(published), 'rejected': int(rejected), 'open_support': int(open_support), 'blocked': int(blocked)}
