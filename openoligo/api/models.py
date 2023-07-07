"""
Tortoise ORM Models for the OpenOligo API
"""
import re
from enum import Enum

from pydantic import BaseModel  # pylint: disable=no-name-in-module
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import ValidationError
from tortoise.models import Model
from tortoise.validators import MinLengthValidator, RegexValidator, Validator

from openoligo.seq import Seq, SeqCategory


class TaskStatus(str, Enum):
    """Status of a synthesis task."""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


class PartType(str, Enum):
    """Type of Sequence Part."""

    TERMINAL3 = "terminal3"
    TERMINAL5 = "terminal5"
    NUCLEOTIDE = "nucleotide"
    MODIFIED_NUCLEOTIDE = "modified_nucleotide"


class ValidSeq(Validator):  # pylint: disable=too-few-public-methods
    """Validate that the value is a valid NA sequence"""

    def __call__(self, value: str) -> None:
        """Validate the value."""
        try:
            Seq(value)
            assert len(value) >= 3, "Sequence must be at least 3 bases long"
            assert len(value) <= 100, "Sequence must be at most 100 bases long"
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        except AssertionError as exc:
            raise ValidationError(str(exc)) from exc


class SynthesisQueue(Model):
    """A synthesis task in the queue."""

    id = fields.IntField(pk=True, autoincrement=True, description="Synthesis ID")

    sequence = fields.TextField(
        validators=[ValidSeq()],
        description="Sequence of the Nucliec Acid to synthesize",
    )
    category = fields.CharEnumField(
        SeqCategory,
        default=SeqCategory.DNA,
        description="Category of the sequence, eg. DNA, RNA, or MIXED",
    )
    status = fields.CharEnumField(TaskStatus, default=TaskStatus.QUEUED)

    rank = fields.IntField(
        default=0,
        description="""Rank of the synthesis task in the queue.
        0 is for chronologically first.
        Other numbers are prioritised over 0 in the increasing order""",
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)

    log_file = fields.TextField(
        null=True,
        validate=[MinLengthValidator(5), RegexValidator(r"\.log$", flags=re.I)],
    )

    class PydanticMeta:  # pylint: disable=too-few-public-methods
        """Pydantic configuration"""

        exclude = ["log_file"]
        ordering = ["-rank", "-created_at"]


class Settings(Model):
    """Settings for this particular instrument."""

    id = fields.IntField(pk=True, autoincrement=True, description="Settings ID")
    org_uuid = fields.TextField(description="UUID of the organisation")
    updated_at = fields.DatetimeField(auto_now_add=True)

    class PydanticMeta:  # pylint: disable=too-few-public-methods
        """Pydantic configuration"""

        ordering = ["-updated_at"]
        exclude = ["id"]


class EssentialReagents(Model):
    """Essential Reagents for this particular instrument."""

    accronym = fields.CharField(
        pk=True, max_length=7, description="Accronym of the reagent", unique=True
    )
    name = fields.TextField(description="Name of the reagent")
    volume = fields.FloatField(description="Volume of the reagents in mL")
    current_volume = fields.FloatField(
        description="Volume of the reagents estimated to be available currently in mL"
    )
    inserted_at = fields.DatetimeField(
        auto_now_add=True, description="When was this reagent inserted?"
    )
    updated_at = fields.DatetimeField(auto_now_add=True, description="Last time this part was used")

    class PydanticMeta:  # pylint: disable=too-few-public-methods
        """Pydantic configuration"""

        ordering = ["current_volume", "-updated_at", "-inserted_at"]


class SequencePartReagents(Model):
    """A part of a sequence, such as nucleotides, or terminal modifications."""

    accronym = fields.CharField(
        pk=True, max_length=7, description="Accronym of the reagent", unique=True
    )
    name = fields.TextField(description="Name of the part")
    volume = fields.FloatField(description="Volume of the part in mL")
    current_volume = fields.FloatField(
        description="Volume of the reagents estimated to be available currently in mL"
    )
    part_type = fields.CharEnumField(PartType, description="Type of sequence part")
    inserted_at = fields.DatetimeField(
        auto_now_add=True, description="When was this reagent inserted?"
    )
    updated_at = fields.DatetimeField(auto_now_add=True, description="Last time this part was used")

    class PydanticMeta:  # pylint: disable=too-few-public-methods
        """Pydantic configuration"""

        ordering = ["current_volume", "-updated_at", "-inserted_at"]


SynthesisQueueModel = pydantic_model_creator(SynthesisQueue, name="SynthesisQueue")

SettingsModel = pydantic_model_creator(Settings, name="Settings")

EssentialReagentsModel = pydantic_model_creator(EssentialReagents, name="EssentialReagents")
SequencePartReagentsModel = pydantic_model_creator(
    SequencePartReagents, name="SequencePartReagents"
)


class AllReagents(BaseModel):  # pylint: disable=too-few-public-methods
    """All reagents in the instrument."""

    reactants: EssentialReagentsModel
    components: SequencePartReagentsModel
