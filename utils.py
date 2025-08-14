import json
import logging
import yaml
from pathlib import Path
from consts import PATH_AI_PRODUCT, PATH_AI_TALENT_HUB, PATH_AI_PRODUCT_PLAN, PATH_AI_TALENT_HUB_PLAN, PATH_PROMPTS


# --- Logging setup ---
def setup_logger() -> logging.Logger:
    """Set up and return logger for the QA bot."""
    LOG_DIR = Path("logs")
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("qa_bot")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_DIR / "chat.log", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(file_handler)
    return logger


def read_program_descriptions(
    path_ai_product: str = None,
    path_ai_talent_hub: str = None,
    path_ai_product_plan: str = None,
    path_ai_talent_hub_plan: str = None,
) -> dict:
    """Read descriptions and study plans of two programs.

    Returns a dict with keys: 'ai_product', 'ai_talent_hub', 'combined'.
    Missing/unreadable files return empty strings.
    """
    if path_ai_product is None:
        path_ai_product = PATH_AI_PRODUCT
    if path_ai_talent_hub is None:
        path_ai_talent_hub = PATH_AI_TALENT_HUB
    if path_ai_product_plan is None:
        path_ai_product_plan = PATH_AI_PRODUCT_PLAN
    if path_ai_talent_hub_plan is None:
        path_ai_talent_hub_plan = PATH_AI_TALENT_HUB_PLAN
        
    logger = setup_logger()
    
    def _safe_read(p: str) -> str:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                return f.read().strip()
        except Exception as e:
            try:
                logger.warning("read_failed | path=%s | err=%s", p, e)
            except Exception:
                pass
            return ""
    
    def _safe_read_json(p: str) -> str:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
                return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            try:
                logger.warning("json_read_failed | path=%s | err=%s", p, e)
            except Exception:
                pass
            return ""

    # Read descriptions
    ai_product_text = _safe_read(path_ai_product)
    ai_talent_hub_text = _safe_read(path_ai_talent_hub)
    
    # Read study plans
    ai_product_plan = _safe_read_json(path_ai_product_plan)
    ai_talent_hub_plan = _safe_read_json(path_ai_talent_hub_plan)
    
    # Combine AI Product info
    ai_product_combined = ai_product_text
    if ai_product_plan:
        ai_product_combined += f"\n\nПлан обучения AI Product Management:\n{ai_product_plan}"
    
    # Combine AI Talent Hub info
    ai_talent_hub_combined = ai_talent_hub_text
    if ai_talent_hub_plan:
        ai_talent_hub_combined += f"\n\nПлан обучения AI Talent Hub:\n{ai_talent_hub_plan}"
    
    # Final combined context
    combined = (
        "AI Product Management:\n" + ai_product_combined + "\n\n" +
        "AI Talent Hub:\n" + ai_talent_hub_combined
    ).strip()

    return {
        "ai_product": ai_product_combined,
        "ai_talent_hub": ai_talent_hub_combined,
        "combined": combined,
    }


def log_request(logger: logging.Logger, session_id: str, model: str,
                programs: list, context_len: int, question: str) -> None:
    """Log chat request details."""
    try:
        logger.info(
            "session=%s | submit | model=%s| programs=%s | context_chars=%d | question=%s",
            session_id, model, programs, context_len, question
        )
    except Exception:
        pass


def log_response(logger: logging.Logger, session_id: str, latency: float, 
                 usage, answer: str) -> None:
    """Log chat response details."""
    try:
        logger.info(
            "session=%s | success | latency_s=%.3f | usage=%s | answer_chars=%d | answer_preview=%s",
            session_id, latency,
            getattr(usage, "model_dump", lambda: usage)() if hasattr(usage, "model_dump") else usage,
            len(answer), answer[:200].replace("\n", " ")
        )
    except Exception:
        pass


def log_error(logger: logging.Logger, session_id: str, error: Exception) -> None:
    """Log chat error."""
    try:
        logger.exception("session=%s | error | %s", session_id, error)
    except Exception:
        pass


def load_prompts(prompts_path: str = None) -> dict:
    """Load prompts from YAML file.
    
    Returns a dict with prompt templates.
    """
    if prompts_path is None:
        prompts_path = PATH_PROMPTS
        
    logger = setup_logger()
    
    try:
        with open(prompts_path, "r", encoding="utf-8") as f:
            prompts = yaml.safe_load(f)
        return prompts or {}
    except Exception as e:
        try:
            logger.warning("prompts_load_failed | path=%s | err=%s", prompts_path, e)
        except Exception:
            pass
        return {
            "system_prompt": "Ты — QA-ассистент. Отвечай только по предоставленному контексту.",
            "context_prompt": "Контекст:\n{context}",
            "no_context_message": "Информация не найдена в контексте.",
            "error_message": "Произошла ошибка."
        }
