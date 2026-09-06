from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    eth_rpc_url: str = "https://eth.llamarpc.com"
    arb_rpc_url: str = "https://arb1.arbitrum.io/rpc"
    base_rpc_url: str = "https://mainnet.base.org"
    opt_rpc_url: str = "https://mainnet.optimism.io"
    polygon_rpc_url: str = "https://polygon-rpc.com"

    alchemy_api_key: str = ""
    infura_api_key: str = ""

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    orbio_model: str = "anthropic/claude-sonnet-4"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    credit_low_threshold_usd: float = 5.0
    scan_interval_seconds: int = 30
    default_chains: str = "ethereum,arbitrum,base"

    @property
    def chains_list(self) -> list[str]:
        return [c.strip() for c in self.default_chains.split(",") if c.strip()]


settings = Settings()
