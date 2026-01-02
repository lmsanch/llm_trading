import os
from dataclasses import dataclass
from typing import Any, Dict, List

import yaml


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    description: str


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    type: str
    model: str | None = None


@dataclass(frozen=True)
class AssetsConfig:
    universe: Dict[str, List[Instrument]]
    rules: Dict[str, Any]
    conviction: Dict[str, Any]
    accounts: List[Account]


@dataclass(frozen=True)
class Checkpoint:
    time: str
    name: str
    description: str


@dataclass(frozen=True)
class ScheduleConfig:
    timezone: str
    weekly_day: str
    weekly_time: str
    checkpoints: List[Checkpoint]
    checkpoint_actions: List[str]
    rules: Dict[str, bool]
    postmortem: Dict[str, str]


@dataclass(frozen=True)
class ModelConfig:
    id: str
    name: str
    openrouter_id: str
    role: str
    enabled: bool


@dataclass(frozen=True)
class ResearchProviderConfig:
    provider: str
    model: str
    api_key_env: str
    enabled: bool


@dataclass(frozen=True)
class ModelsConfig:
    research: Dict[str, ResearchProviderConfig]
    pm_models: List[ModelConfig]
    chairman: Dict[str, Any]
    openrouter: Dict[str, Any]
    title_generation: Dict[str, Any]
    model_settings: Dict[str, Any]
    validation: Dict[str, Any]
    logging: Dict[str, Any]


@dataclass(frozen=True)
class AppConfig:
    assets: AssetsConfig
    schedule: ScheduleConfig
    models: ModelsConfig
    environment: Dict[str, str]


def _load_yaml(path: str) -> Dict[str, Any]:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, "config", os.path.basename(path))

    with open(config_path) as f:
        return yaml.safe_load(f)


def _parse_instruments(data: List[Dict[str, str]]) -> List[Instrument]:
    return [
        Instrument(item["symbol"], item["name"], item["description"]) for item in data
    ]


def _parse_accounts(data: List[Dict[str, Any]]) -> List[Account]:
    accounts = []
    for item in data:
        accounts.append(
            Account(
                id=item["id"],
                name=item["name"],
                type=item["type"],
                model=item.get("model"),
            )
        )
    return accounts


def _parse_universe(
    data: Dict[str, List[Dict[str, str]]],
) -> Dict[str, List[Instrument]]:
    return {key: _parse_instruments(items) for key, items in data.items()}


def _parse_checkpoints(data: List[Dict[str, str]]) -> List[Checkpoint]:
    return [
        Checkpoint(item["time"], item["name"], item["description"]) for item in data
    ]


def _parse_pm_models(data: List[Dict[str, Any]]) -> List[ModelConfig]:
    return [
        ModelConfig(
            id=item["id"],
            name=item["name"],
            openrouter_id=item["openrouter_id"],
            role=item["role"],
            enabled=item["enabled"],
        )
        for item in data
    ]


def _parse_research_providers(
    data: Dict[str, Dict[str, Any]],
) -> Dict[str, ResearchProviderConfig]:
    return {
        key: ResearchProviderConfig(
            provider=value["provider"],
            model=value["model"],
            api_key_env=value["api_key_env"],
            enabled=value["enabled"],
        )
        for key, value in data.items()
    }


def load_assets_config() -> AssetsConfig:
    data = _load_yaml("assets.yaml")

    return AssetsConfig(
        universe=_parse_universe(data["universe"]),
        rules=data["rules"],
        conviction=data["conviction"],
        accounts=_parse_accounts(data["accounts"]),
    )


def load_schedule_config() -> ScheduleConfig:
    data = _load_yaml("schedule.yaml")
    schedule = data["schedule"]

    return ScheduleConfig(
        timezone=schedule["timezone"],
        weekly_day=schedule["weekly_day"],
        weekly_time=schedule["weekly_time"],
        checkpoints=_parse_checkpoints(data["checkpoints"]),
        checkpoint_actions=data["checkpoint_actions"],
        rules=data["rules"],
        postmortem=data["postmortem"],
    )


def load_models_config() -> ModelsConfig:
    data = _load_yaml("models.yaml")

    return ModelsConfig(
        research=_parse_research_providers(data["research"]),
        pm_models=_parse_pm_models(data["pm_models"]),
        chairman=data["chairman"],
        openrouter=data["openrouter"],
        title_generation=data["title_generation"],
        model_settings=data["model_settings"],
        validation=data["validation"],
        logging=data["logging"],
    )


def load_environment() -> Dict[str, str]:
    env_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    )

    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

    required_keys = ["OPENROUTER_API_KEY", "APCA_API_KEY_ID", "APCA_API_SECRET_KEY"]
    missing = [key for key in required_keys if not os.environ.get(key)]

    if missing:
        raise EnvironmentError(f"Missing required environment variables: {missing}")

    return {
        "OPENROUTER_API_KEY": os.environ["OPENROUTER_API_KEY"],
        "APCA_API_KEY_ID": os.environ["APCA_API_KEY_ID"],
        "APCA_API_SECRET_KEY": os.environ["APCA_API_SECRET_KEY"],
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
        "PERPLEXITY_API_KEY": os.environ.get("PERPLEXITY_API_KEY", ""),
        "DATABASE_URL": os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/llm_trading"
        ),
    }


def load_config() -> AppConfig:
    return AppConfig(
        assets=load_assets_config(),
        schedule=load_schedule_config(),
        models=load_models_config(),
        environment=load_environment(),
    )
