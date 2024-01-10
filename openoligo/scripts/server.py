"""
Script to start the REST API server for OpenOligo.
"""
from typing import Optional

import uvicorn
from fastapi import Body, FastAPI, HTTPException, Query, status
from tortoise.exceptions import ValidationError

from openoligo.api.db import db_init, get_db_url

# from openoligo.api.models import Settings  # pylint: disable=unused-import
from openoligo.api.models import (  # EssentialReagentsModel,; SequencePartReagentsModel,
    InstrumentHealth,
    NucleotidesModel,
    Reactant,
    ReactantModel,
    ReactantType,
    Settings,
    SettingsModel,
    SolidSupport,
    SynthesisTask,
    SynthesisTaskModel,
    TaskStatus,
    ValidSeq,
)
from openoligo.hal.platform import __platform__
from openoligo.utils.logger import OligoLogger

ol = OligoLogger(name="server", rotates=True)
logger = ol.get_logger()

rl = OligoLogger(rotates=True)
root_logger = rl.get_logger()

DESCRIPTION = """
OpenOligo API for the synthesis of oligonucleotides.

You can
* Request a new oligo synthesis task.
* Check the status of the sequences waiting to be synthesized.
* Read and Update the configuration and the staus of the instrument.

## SynthesisTask

You will be able to:

* **Add a Sequence** to the Synthesis Queue.
* **Update the sequence and order of synthesis**.
* **Check the status** of a Sequence in the Queue.
* **Remove a Sequence** from the Queue.

## Instrument

You will be able to:

* **Read the configuration** of the instrument (_not implemented_).
* **Update the configuration** of the instrument (_not implemented_).
* **Read the status** of the instrument (_not implemented_).
* **Update the status** of the instrument (_not implemented_).
"""


app = FastAPI(
    title="OpenOligo API",
    summary="REST API for OpenOligo",
    description=DESCRIPTION,
    version="0.1.6",
    contact={
        "name": "Satyam Tiwary",
        "email": "satyam@technoculture.io",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)


@app.on_event("startup")
async def startup_event():
    """Startup event for the FastAPI server."""
    logger.info("Starting the API server...")  # pragma: no cover
    db_url = get_db_url(__platform__)  # pragma: no cover
    logger.info("Using database: '%s'", db_url)  # pragma: no cover
    await db_init(db_url)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event for the FastAPI server."""
    logger.info("Shutting down the API server...")


@app.get("/health", status_code=200, tags=["Utilities"])
def get_health_status():
    """Health check."""
    return {"status": InstrumentHealth.OPERATIONAL}


@app.post(
    "/queue",
    status_code=status.HTTP_201_CREATED,
    response_model=SynthesisTaskModel,
    tags=["Synthesis Queue"],
)
async def add_a_task_to_synthesis_queue(
    sequence: NucleotidesModel, solid_support: SolidSupport, rank: int = 0
):
    """Add a synthesis task to the synthesis task queue by providing a sequence and its category."""
    try:
        task = await SynthesisTask.create(sequence=sequence, solid_support=solid_support, rank=rank)
        # return { "status": task.status, "created_at": task.created_at }
        return task
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        logger.info("Added sequence '%s' to the synthesis queue.", sequence)


@app.get(
    "/queue",
    response_model=list[SynthesisTaskModel],  # type: ignore
    status_code=status.HTTP_200_OK,
    tags=["Synthesis Queue"],
)
async def get_all_tasks_in_synthesis_queue(filter_by: Optional[TaskStatus] = None):
    """Get the current synthesis task queue."""
    tasks = SynthesisTask.all().order_by("-rank", "-created_at")
    if filter_by:
        tasks = tasks.filter(status=filter)
    return await tasks


@app.delete("/queue", status_code=status.HTTP_200_OK, tags=["Synthesis Queue"])
async def clear_all_queued_tasks_in_task_queue():
    """Delete all tasks in the QUEUED state."""
    return await SynthesisTask.filter(status=TaskStatus.WAITING_IN_QUEUE).delete()


@app.get("/queue/{task_id}", response_model=SynthesisTaskModel, tags=["Synthesis Queue"])
async def get_task_by_id(task_id: int):
    """Get a synthesis task from the queue."""
    task = await SynthesisTask.get_or_none(id=task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sythesis task not found")
    return task


@app.put(
    "/queue/{task_id}",
    response_model=SynthesisTaskModel,
    status_code=status.HTTP_200_OK,
    tags=["Synthesis Queue"],
)
async def update_a_synthesis_task(
    task_id: int, sequence: NucleotidesModel, rank: Optional[int] = Body(None)
):
    """Update a particular task in the queue."""
    task = await SynthesisTask.get_or_none(id=task_id)

    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence task not found")

    if task.status != TaskStatus.WAITING_IN_QUEUE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Sequence task not in QUEUED state"
        )

    if sequence is None and rank is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"""Nothing to update. Provide sequence or rank.
(Sequence: {sequence}, Rank: {rank})""",
        )

    if sequence is not None:
        try:
            seq_validator = ValidSeq()
            # seq_validator(sequence)
            task.sequence = sequence  # type: ignore
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if rank is not None and rank != task.rank:
        task.rank = rank  # type: ignore

    await task.save()

    return task


@app.delete("/queue/{task_id}", status_code=status.HTTP_200_OK, tags=["Synthesis Queue"])
async def delete_synthesis_task_by_id(task_id: int):
    """Delete a synthesis task from the queue."""
    task = await SynthesisTask.get_or_none(id=task_id)

    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")

    await task.delete()

    return task


@app.get(
    "/about",
    tags=["Instrument"],
    response_model=SettingsModel,  # type: ignore
    status_code=status.HTTP_200_OK,
)
async def get_instrument_info():
    """Get information about the instrument."""
    settings = await Settings.all().order_by("-created_at").first()
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instrument not configured with an Organisation",
        )
    return settings


@app.post(
    "/about",
    tags=["Instrument"],
    response_model=SettingsModel,  # type: ignore
    status_code=status.HTTP_201_CREATED,
)
async def post_instrument_info(
    org_uuid: str = Query(
        ..., alias="organisation", description="Organisation UUID", min_length=8, max_length=36
    ),
):
    """Post information about the instrument."""
    try:
        return await Settings.create(
            org_uuid=org_uuid,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get(
    "/reagents",
    tags=["Instrument"],
    status_code=status.HTTP_200_OK,
    response_model=list[ReactantModel],  # type: ignore
)
async def get_all_reagents():
    """Get all reagents."""
    return await Reactant.all()


@app.post(
    "/reagents",
    tags=["Instrument"],
    status_code=status.HTTP_201_CREATED,
    response_model=ReactantModel,
)
async def add_reagent_to_inventory(
    name: str = Query(..., min_length=1, max_length=100),
    accronym: str = Query(
        description="Exact representation of the reagent in a Sequence",
        example="5mC, -GalNAc, U, T, etc.",
        min_length=1,
        max_length=10,
        regex=r"^[A-Za-z0-9\-]+$",
    ),
    volume_in_ml: float = Query(0.0, ge=0.0, le=1000.0),
    reactant_type: ReactantType = ReactantType.REACTANT,
):
    """Add a reagent to the inventory."""
    try:
        model = await Reactant.create(
            name=name,
            accronym=accronym,
            volume=volume_in_ml,
            reactant_type=reactant_type,
            current_volume=volume_in_ml,
        )
        return model
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        logger.info("Added reagent '%s' to the inventory.", name)


def main():
    """Main function to start the server."""
    uvicorn.run(
        "openoligo.scripts.server:app", host="0.0.0.0", port=9191, reload=True
    )  # pragma: no cover


if __name__ == "__main__":
    main()  # pragma: no cover
