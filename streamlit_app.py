import os
import time
import uuid
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from utils import setup_logger, read_program_descriptions, log_request, log_response, log_error, load_prompts
from consts import (
    APP_TITLE, DEFAULT_MODEL,
    PROGRAM_AI_PRODUCT, PROGRAM_AI_TALENT_HUB
)

load_dotenv()
logger = setup_logger()

def ensure_openai_settings() -> None:
    with st.sidebar:
        st.subheader("OpenAI настройки")
        # Try to get API key from multiple sources
        api_key = (
            os.environ.get("OPENAI_API_KEY") or 
            st.secrets.get("OPENAI_API_KEY", None) or
            st.secrets.get("openai", {}).get("api_key", None)
        )
        
        if api_key:
            st.success("✅ API ключ загружен")
        else:
            st.warning("⚠️ API ключ не найден")
            st.info("Добавьте OPENAI_API_KEY в секреты Streamlit или переменные окружения")
        
        st.divider()
        if st.button("Сбросить диалог"):
            st.session_state.messages = []
            # Add welcome message after reset
            prompts = load_prompts()
            welcome_msg = prompts.get("welcome_message", "Привет! Я помогу вам с вопросами о магистерских программах ИТМО.")
            st.session_state.messages.append(("assistant", welcome_msg))


def init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Add welcome message from bot
        prompts = load_prompts()
        welcome_msg = prompts.get("welcome_message", "Привет! Я помогу вам с вопросами о магистерских программах ИТМО.")
        st.session_state.messages.append(("assistant", welcome_msg))
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🎓", layout="wide")
    st.title(APP_TITLE)
    st.caption("Чат-бот, помогающий с выбором программы ITMO.")

    init_state()
    ensure_openai_settings()

    

    with st.sidebar:
        st.header("Параметры программ и контекст")
        program_a = st.text_input("Программа 1", value=PROGRAM_AI_PRODUCT)
        program_b = st.text_input("Программа 2", value=PROGRAM_AI_TALENT_HUB)
        context = read_program_descriptions()['combined']
        context = st.text_input("Контекст", value=context)
        

    for role, content in st.session_state.messages:
        with st.chat_message(role):
            st.markdown(content)

    user_msg = st.chat_input("Ваш вопрос об этих программах…")
    if user_msg:
        with st.chat_message("user"):
            st.markdown(user_msg)
        st.session_state.messages.append(("user", user_msg))

        # Get API key from multiple sources
        api_key = (
            os.environ.get("OPENAI_API_KEY") or 
            st.secrets.get("OPENAI_API_KEY", None) or
            st.secrets.get("openai", {}).get("api_key", None)
        )
        
        if not api_key:
            st.error("❌ Не найден OPENAI_API_KEY. Добавьте ключ в секреты Streamlit или переменные окружения.")
            st.stop()
        
        client = OpenAI(api_key=api_key, base_url="https://api.proxyapi.ru/openai/v1")

        # Load prompts from YAML
        prompts = load_prompts()
        system_prompt = prompts.get("system_prompt", "Ты — QA-ассистент.")
        context_prompt = prompts.get("context_prompt", "Контекст:\n{context}").format(context=(context or '').strip())

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": context_prompt},
        ]
        for r, c in st.session_state.messages:
            if r in ("user", "assistant"):
                messages.append({"role": r, "content": c})
        messages.append({"role": "user", "content": user_msg.strip()})

        # Log request
        log_request(
            logger, st.session_state.session_id, DEFAULT_MODEL,
            [program_a.strip(), program_b.strip()], 
            len(context or ""), user_msg.strip()
        )

        with st.spinner("Получаю ответ от OpenAI…"):
            try:
                t0 = time.perf_counter()
                completion = client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=messages,
                )
                answer = completion.choices[0].message.content.strip()
                latency = time.perf_counter() - t0
                usage = getattr(completion, "usage", None)
                log_response(logger, st.session_state.session_id, latency, usage, answer)
            except Exception as e:
                answer = f"Ошибка: {e}"
                log_error(logger, st.session_state.session_id, e)

        with st.chat_message("assistant"):
            st.markdown(answer)
        st.session_state.messages.append(("assistant", answer))


if __name__ == "__main__":
    main()
