from datetime import datetime

import pytest
from tortoise.exceptions import ValidationError

from openoligo.api.models import SynthesisTask, SynthesisTaskModel, TaskStatus
from openoligo.seq import SeqCategory


@pytest.mark.asyncio
async def test_create_synthesis_queue(db):
    synthesis_queue = await SynthesisTask.create(
        sequence="ATCG", category=SeqCategory.DNA, status=TaskStatus.QUEUED, rank=0
    )

    assert synthesis_queue.id == 1
    assert synthesis_queue.sequence == "ATCG"
    assert synthesis_queue.status == TaskStatus.QUEUED
    assert synthesis_queue.rank == 0


@pytest.mark.asyncio
async def test_synthesis_queue_validation(db):
    with pytest.raises(ValidationError):
        await SynthesisTask.create(
            sequence="ATXG",  # Invalid Sequence
            status=TaskStatus.QUEUED,
            rank=0,
        )


@pytest.mark.asyncio
async def test_update_synthesis_queue_status(db):
    synthesis_queue = await SynthesisTask.create(sequence="ATCG", status=TaskStatus.QUEUED, rank=0)

    await synthesis_queue.all().update(status=TaskStatus.IN_PROGRESS)
    synthesis_queue_updated = await SynthesisTask.get(id=synthesis_queue.id)

    assert synthesis_queue_updated.status == TaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_pydantic_model_queue(db):
    t = datetime.now()
    model = SynthesisTaskModel(
        id=101,
        sequence="ATCG",
        status=TaskStatus.QUEUED,
        rank=0,
        created_at=t,
    )

    assert model.id == 101
    assert model.sequence == "ATCG"
    assert model.status == TaskStatus.QUEUED
    assert model.rank == 0
    assert isinstance(model.created_at, datetime)
    assert model.created_at == t
