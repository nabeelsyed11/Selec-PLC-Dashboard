"""
Core Application Settings & Configuration
Loads from environment variables and .env file with safe defaults.
"""
from pathlib import Path
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General App Config
    ENV: Literal["development", "production", "test"] = "development"
    LOG_LEVEL: str = "INFO"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    PROJECT_NAME: str = "Selec MiBRX-6M Industrial IoT Gateway"

    # PLC Connection Settings
    PLC_HOST: str = "192.168.1.50"
    PLC_PORT: int = 502
    PLC_UNIT_ID: int = 1
    PLC_TIMEOUT_SECONDS: float = 1.5
    SIMULATION_MODE: bool = False

    # Register Map Configuration
    REGISTER_MAP_PATH: str = str(BASE_DIR / "config" / "register_map.yaml")

    # Safe Remote Control (Disabled by Default)
    ALLOW_REMOTE_CONTROL: bool = False
    CONTROL_TOKEN_SECRET: str = "default-insecure-dev-key-change-in-production"
    OPERATOR_USERNAME: str = "operator"
    OPERATOR_PASSWORD_HASH: str = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # 'operator123'
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"     # 'admin123'

    # Vibration Sensor Configuration
    VIBRATION_SENSOR_INTERFACE: Literal[
        "MOCK", "I2C_ADXL345", "I2C_MPU6050", "SPI_ADXL355", "ADC_ADS1115", "GPIO_DIGITAL"
    ] = "GPIO_DIGITAL"
    VIBRATION_GPIO_PIN: int = 17
    VIBRATION_SAMPLE_RATE_HZ: int = 1000
    VIBRATION_BUFFER_SIZE: int = 512
    VIBRATION_WARNING_RMS_G: float = 1.8
    VIBRATION_CRITICAL_RMS_G: float = 3.5

    # Database & Data Retention
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'selec_iot.db'}"
    DATA_DIR: str = str(BASE_DIR / "data")
    DATA_RETENTION_HOURS: int = 720
    MEASUREMENT_BUFFER_FLUSH_SEC: float = 1.0

    # Latency Benchmark Defaults
    BENCHMARK_DURATION_SECONDS: int = 60
    BENCHMARK_TARGET_POLL_MS: int = 200


settings = Settings()
