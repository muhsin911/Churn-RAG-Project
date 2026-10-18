"""Validated API request and response models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CustomerFeatures(BaseModel):
    """Nineteen non-identifier customer profile features used for churn risk."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tenure: int = Field(ge=0, le=120, description="Months the customer has stayed")
    monthly_charges: float = Field(gt=0, le=100_000)
    total_charges: float | None = Field(default=None, ge=0, le=10_000_000)
    senior_citizen: int | None = Field(default=None, ge=0, le=1)
    gender: Literal["Female", "Male", "Unknown"] | None = None
    partner: Literal["Yes", "No", "Unknown"] | None = None
    dependents: Literal["Yes", "No", "Unknown"] | None = None
    phone_service: Literal["Yes", "No", "Unknown"] | None = None
    multiple_lines: Literal["Yes", "No", "No phone service", "Unknown"] | None = None
    internet_service: Literal["DSL", "Fiber optic", "No", "Unknown"] | None = None
    online_security: Literal["Yes", "No", "No internet service", "Unknown"] | None = None
    online_backup: Literal["Yes", "No", "No internet service", "Unknown"] | None = None
    device_protection: Literal["Yes", "No", "No internet service", "Unknown"] | None = None
    tech_support: Literal["Yes", "No", "No internet service", "Unknown"] | None = None
    streaming_tv: Literal["Yes", "No", "No internet service", "Unknown"] | None = None
    streaming_movies: Literal["Yes", "No", "No internet service", "Unknown"] | None = None
    contract_type: Literal["Month-to-month", "One year", "Two year"]
    paperless_billing: Literal["Yes", "No", "Unknown"] | None = None
    payment_method: Literal[
        "Electronic check",
        "Mailed check",
        "Bank transfer",
        "Credit card",
    ]

    @model_validator(mode="after")
    def derive_total_charges(self) -> "CustomerFeatures":
        """Use tenure and monthly charges when total charges were not supplied."""
        if self.total_charges is None:
            self.total_charges = round(self.tenure * self.monthly_charges, 2)
        return self


class PredictionResponse(BaseModel):
    """Churn classification and estimated probability."""

    churn_prediction: bool
    churn_probability: float = Field(ge=0, le=1)
    message: str
    baseline_probability: float = Field(ge=0, le=1)
    explanations: list["FeatureContribution"]


class FeatureContribution(BaseModel):
    """Grouped SHAP contribution for one original input feature."""

    feature: str
    value: str
    impact: float


class ChatRequest(BaseModel):
    """Question submitted to the customer-data assistant."""

    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=2_000)


class ChatResponse(BaseModel):
    """Generated answer with customer-record references."""

    answer: str
    sources: list[str] = Field(default_factory=list)


class CustomerCreate(BaseModel):
    """Customer data accepted when creating one database record."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    customer_id: str | None = Field(default=None, min_length=1, max_length=64)
    tenure: int = Field(ge=0, le=120)
    monthly_charges: float = Field(gt=0, le=100_000)
    total_charges: float = Field(ge=0, le=10_000_000)
    contract_type: Literal["Month-to-month", "One year", "Two year"]
    payment_method: Literal[
        "Electronic check",
        "Mailed check",
        "Bank transfer",
        "Credit card",
    ]
    gender: str | None = None
    senior_citizen: int | None = Field(default=None, ge=0, le=1)
    partner: str | None = None
    dependents: str | None = None
    phone_service: str | None = None
    multiple_lines: str | None = None
    internet_service: str | None = None
    online_security: str | None = None
    online_backup: str | None = None
    device_protection: str | None = None
    tech_support: str | None = None
    streaming_tv: str | None = None
    streaming_movies: str | None = None
    paperless_billing: str | None = None
    actual_churn: bool | None = None

    @model_validator(mode="after")
    def validate_total_charges(self) -> "CustomerCreate":
        """Allow zero charges only for customers with zero tenure."""
        if self.tenure > 0 and self.total_charges <= 0:
            raise ValueError("total_charges must be positive when tenure is positive.")
        return self


class CustomerPatch(BaseModel):
    """Fields that may be changed on one existing customer."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    tenure: int | None = Field(default=None, ge=0, le=120)
    monthly_charges: float | None = Field(default=None, gt=0, le=100_000)
    total_charges: float | None = Field(default=None, ge=0, le=10_000_000)
    contract_type: Literal["Month-to-month", "One year", "Two year"] | None = None
    payment_method: Literal[
        "Electronic check",
        "Mailed check",
        "Bank transfer",
        "Credit card",
    ] | None = None
    gender: str | None = None
    senior_citizen: int | None = Field(default=None, ge=0, le=1)
    partner: str | None = None
    dependents: str | None = None
    phone_service: str | None = None
    multiple_lines: str | None = None
    internet_service: str | None = None
    online_security: str | None = None
    online_backup: str | None = None
    device_protection: str | None = None
    tech_support: str | None = None
    streaming_tv: str | None = None
    streaming_movies: str | None = None
    paperless_billing: str | None = None
    actual_churn: bool | None = None


class ChurnSegment(BaseModel):
    """Observed churn rate for one dataset category."""

    feature: str
    category: str
    customers: int
    churned: int
    churn_rate: float


class DatasetSummaryResponse(BaseModel):
    """Exact, descriptive statistics computed from the complete dataset."""

    total_customers: int
    churn_count: int
    retained_count: int
    churn_rate: float
    segments: list[ChurnSegment]
    known_actual_outcomes: int = 0
    unlabeled_customers: int = 0


class CustomerResponse(BaseModel):
    """Customer profile and separate model prediction/actual outcome values."""

    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    tenure: int
    monthly_charges: float
    total_charges: float
    contract_type: str
    payment_method: str
    gender: str | None
    senior_citizen: int | None
    partner: str | None
    dependents: str | None
    phone_service: str | None
    multiple_lines: str | None
    internet_service: str | None
    online_security: str | None
    online_backup: str | None
    device_protection: str | None
    tech_support: str | None
    streaming_tv: str | None
    streaming_movies: str | None
    paperless_billing: str | None
    actual_churn: bool | None
    predicted_churn: bool | None
    churn_probability: float | None
    record_source: str
    created_at: datetime
    updated_at: datetime


class CustomerPage(BaseModel):
    """One page of database records."""

    items: list[CustomerResponse]
    page: int
    page_size: int
    total: int
    total_pages: int