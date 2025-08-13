# app/services/followup.py
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, or_
from app.models.followup_state import FollowUpState
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

TEN_MIN = timedelta(minutes=10)

class FollowUpService:
    @staticmethod
    async def mark_user_msg(session, phone: str):
        st = await session.get(FollowUpState, phone)
        if not st:
            st = FollowUpState(phone=phone, last_actor="user", schedule_confirmed=False)
            session.add(st)
        else:
            st.last_actor = "user"
            # RESET de tentativas ao receber msg do usuário
            st.followup_count = 0
            st.last_followup_at = None
        st.updated_at = datetime.now(timezone.utc)
        await session.commit()

    @staticmethod
    async def mark_ai_reply(session, phone: str, schedule_done: bool = False):
        st = await session.get(FollowUpState, phone)
        if not st:
            st = FollowUpState(phone=phone)
            session.add(st)
        st.last_actor = "ai"
        st.last_ai_at = datetime.now(timezone.utc)
        if schedule_done:
            st.schedule_confirmed = True
            # se quiser, também zere contadores
            st.followup_count = 0
            st.last_followup_at = None
        st.updated_at = datetime.now(timezone.utc)
        await session.commit()

    @staticmethod
    async def mark_followup_attempt(session, phone: str):
        """Chame depois de enviar um nudge."""
        st = await session.get(FollowUpState, phone)
        if st:
            st.followup_count = (st.followup_count or 0) + 1
            st.last_followup_at = datetime.now(timezone.utc)
            st.updated_at = st.last_followup_at
            await session.commit()

    @staticmethod
    async def candidates(session):
        """
        Quem deve receber nudge agora?
        - última interação da IA
        - não concluiu agendamento
        - menos de 3 tentativas
        - se nunca tentou: 10 min desde last_ai_at
        - se já tentou: 10 min desde last_followup_at
        """
        now = datetime.now(timezone.utc)
        q = (
            select(FollowUpState)
            .where(FollowUpState.last_actor == "ai")
            .where(FollowUpState.schedule_confirmed.is_(False))
            .where((FollowUpState.followup_count < 1))
            .where(
                or_(
                    # sem tentativas ainda
                    (FollowUpState.last_followup_at.is_(None) & (FollowUpState.last_ai_at <= now - TEN_MIN)),
                    # já tentou, respeitar janela de 10min desde a última tentativa
                    (FollowUpState.last_followup_at.is_not(None) & (FollowUpState.last_followup_at <= now - TEN_MIN)),
                )
            )
        )
        res = await session.execute(q)
        return list(res.scalars())
    
    @staticmethod
    async def delete_fllow_up_by_phone(session: AsyncSession, phone: str) -> bool:
        try:
            stmt = delete(FollowUpState).where(FollowUpState.phone == phone)
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as e:
            return False
