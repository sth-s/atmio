from typing import List, Optional
from pydantic import BaseModel, Field

class Contact(BaseModel):
    name: str = Field(..., description="Full name of the contact")
    email: Optional[str] = Field(None, description="Email address")
    role: Optional[str] = Field(None, description="Job title or role")

class Metrics(BaseModel):
    revenue: Optional[float] = Field(None, description="Annual revenue")
    employees: Optional[int] = Field(None, description="Total number of employees")
    growth_rate: Optional[float] = Field(None, description="Year-over-year growth rate")

class CompanyInfo(BaseModel):
    name: str = Field(..., description="Company name")
    description: Optional[str] = Field(None, description="Brief company description")
    industry: Optional[str] = Field(None, description="Primary industry sector")
    website: Optional[str] = Field(None, description="Company website URL")
    contacts: List[Contact] = Field(default_factory=list, description="List of key contacts")
    metrics: Optional[Metrics] = Field(None, description="Key financial metrics")
