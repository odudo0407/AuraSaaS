"""SQLAlchemy ORM models — AuraSaaS multi-store BI, RAG, HITL and trace data."""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User accounts for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    email = Column(String(120), nullable=False, unique=True, index=True)
    password_hash = Column(String(200), nullable=False)
    avatar_url = Column(String(500), default="")
    created_at = Column(DateTime, server_default=func.now())


class Store(Base):
    """Multi-store architecture."""
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)                    # 门店名称
    city = Column(String(50))                                      # 城市
    address = Column(String(300))                                  # 地址
    area = Column(String(50))                                      # 商圈/区域（兼容旧 Demo）
    store_type = Column(String(50), default="coffee_shop")         # coffee_shop/restaurant/retail
    opened_at = Column(Date)                                       # 开业日期
    manager_name = Column(String(50))                              # 店长
    status = Column(String(20), default="open")                    # open/closed
    seats = Column(Integer, default=0)                             # 座位数
    staff_count = Column(Integer, default=0)                       # 员工数
    rating = Column(Float, default=4.5)                            # 评分
    created_at = Column(DateTime, server_default=func.now())

    metrics = relationship("BusinessMetricsDaily", back_populates="store")
    sku_records = relationship("SkuPerformance", back_populates="store")
    external_factors = relationship("ExternalFactor", back_populates="store")
    memories = relationship("AgentMemory", back_populates="store")
    staff = relationship("Staff", back_populates="store")


class Staff(Base):
    """Store staff / employees."""
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(30), default="")
    role = Column(String(30), default="staff")          # manager / staff / chef / barista / cashier
    email = Column(String(120), default="")
    id_number = Column(String(30), default="")          # 身份证号
    hire_date = Column(Date, nullable=True)
    status = Column(String(20), default="active")       # active / leave / resigned
    salary = Column(Float, default=0)
    notes = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    store = relationship("Store", back_populates="staff")


class BusinessMetricsDaily(Base):
    """Daily core business metrics — per store."""
    __tablename__ = "business_metrics_daily"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # TODO-compatible fields
    revenue = Column(Float, nullable=False, default=0)
    order_count = Column(Integer, nullable=False, default=0)
    avg_ticket = Column(Float, nullable=False, default=0)
    gross_margin = Column(Float, nullable=False, default=0)
    refund_rate = Column(Float, default=0)
    delivery_ratio = Column(Float, default=0)
    dine_in_ratio = Column(Float, default=0)
    new_customers = Column(Integer, default=0)
    returning_customers = Column(Integer, default=0)

    # Existing frontend/API compatibility fields
    total_revenue = Column(Float, nullable=False, default=0)
    avg_order_value = Column(Float, nullable=False, default=0)
    platform_commission = Column(Float, nullable=False, default=0)
    net_profit = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())

    store = relationship("Store", back_populates="metrics")


class SkuPerformance(Base):
    """SKU performance — per store."""
    __tablename__ = "sku_performance"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    sku_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    image_url = Column(String(500), default="")
    price = Column(Float, nullable=False, default=0)

    # TODO-compatible + existing compatibility fields
    sales_count = Column(Integer, nullable=False, default=0)
    sales_volume = Column(Integer, nullable=False, default=0)
    revenue = Column(Float, nullable=False, default=0)
    cost = Column(Float, nullable=False, default=0)
    gross_margin = Column(Float, nullable=False, default=0)
    refund_rate = Column(Float, default=0)
    stockout_count = Column(Integer, default=0)
    cost_warning = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    store = relationship("Store", back_populates="sku_records")


class ExternalFactor(Base):
    """External factors for attribution analysis."""
    __tablename__ = "external_factors"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), index=True)
    date = Column(Date, nullable=False, index=True)

    # TODO-compatible fields
    weather = Column(String(50))
    temperature = Column(Float)
    is_holiday = Column(Boolean, default=False)
    holiday_name = Column(String(100))
    nearby_event = Column(String(200))
    traffic_level = Column(String(20))
    note = Column(Text)

    # Existing compatibility fields
    factor_type = Column(String(50), nullable=False, default="note")       # weather/holiday/event
    description = Column(String(200), nullable=False, default="无特殊因素")
    impact_level = Column(String(20), default="medium")                    # low/medium/high
    created_at = Column(DateTime, server_default=func.now())

    store = relationship("Store", back_populates="external_factors")


class MarketingCampaign(Base):
    """Marketing campaign records."""
    __tablename__ = "marketing_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), index=True)
    campaign_name = Column(String(200), nullable=False)
    channel = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    target_audience = Column(String(100))
    budget = Column(Float, default=0)
    conversion_rate = Column(Float, default=0)
    spend = Column(Float, default=0)
    revenue_generated = Column(Float, default=0)
    content_text = Column(String(2000))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CampaignResult(Base):
    """Campaign effect review records."""
    __tablename__ = "campaign_results"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("marketing_campaigns.id"), index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), index=True)
    revenue_lift = Column(Float, default=0)
    order_lift = Column(Integer, default=0)
    roi = Column(Float, default=0)
    summary = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class KnowledgeDocument(Base):
    """RAG knowledge base documents."""
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    source = Column(String(300))
    category = Column(String(80))
    doc_type = Column(String(50), nullable=False)                  # sop/case/template
    content = Column(Text, nullable=False)
    tags = Column(String(500))                                     # comma-separated
    created_at = Column(DateTime, server_default=func.now())



class TenantKnowledgeDocument(Base):
    """Tenant-scoped private knowledge documents for business RAG."""
    __tablename__ = "tenant_knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    file_name = Column(String(300), nullable=False, index=True)
    file_size = Column(Integer, nullable=False, default=0)
    file_type = Column(String(20), nullable=False)
    source_path = Column(String(600), nullable=False, default="")
    content_hash = Column(String(64), nullable=False, index=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="pending", index=True)
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now(), index=True)
    created_by = Column(String(100), nullable=True)

class AgentMemory(Base):
    """Long-term operation memory for stores and users."""
    __tablename__ = "agent_memories"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), index=True)
    memory_type = Column(String(50), nullable=False)                # user_preference/store_issue/etc.
    content = Column(Text, nullable=False)
    tags = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    store = relationship("Store", back_populates="memories")


class AgentTrace(Base):
    """Agent execution trace for timeline and replay."""
    __tablename__ = "agent_traces"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String(100), nullable=False, unique=True, index=True)
    user_query = Column(Text, nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), index=True)
    status = Column(String(20), default="running")
    steps_json = Column(Text, default="[]")
    final_answer = Column(Text)
    graph_state = Column(Text, nullable=True)  # JSON-serialized AgentState for HITL resume
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AgentApproval(Base):
    """HITL approval records."""
    __tablename__ = "agent_approvals"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    trace_id = Column(String(100), ForeignKey("agent_traces.trace_id"), index=True)
    node_name = Column(String(50), nullable=False)
    proposal = Column(Text, nullable=False)                        # AI 生成的策略提案
    estimated_cost = Column(Float, default=0)
    status = Column(String(20), default="pending")                 # pending/approved/rejected/revise
    reviewer_comment = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    reviewed_at = Column(DateTime)


class Task(Base):
    """Pending tasks and alerts for the dashboard."""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    task_type = Column(String(50), nullable=False)          # inventory/cost/marketing/report/store/system
    urgency = Column(String(20), default="low")             # high/medium/low
    status = Column(String(20), default="pending")          # pending/done/dismissed
    icon = Column(String(10), default="📋")
    tag = Column(String(50), default="系统")
    link_to = Column(String(100))                           # frontend route to navigate on click
    related_id = Column(Integer)                            # related entity id
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
