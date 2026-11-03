from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import TimestampedModel


class User(TimestampedModel):
    """
    User model representing both EV Customers and Network Administrators.
    """
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="Unique email address used for login",
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Bcrypt-hashed password string",
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Full name of user",
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default="CUSTOMER",
        nullable=False,
        doc="Role-based access: 'CUSTOMER' or 'ADMIN'",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Flag indicating if the user account is active",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"

