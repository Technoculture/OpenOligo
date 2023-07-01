"""
Script to start the REST API server for OpenOligo.
"""
import logging
import uvicorn
from tortoise import Tortoise
from fastapi import FastAPI, HTTPException
from tortoise.exceptions import ValidationError

from api.models import (
    SequenceJob,
    InstrumentStatus,
    JobModelIn,
    JobModelOut,
    InstrumentStatusModelOut,
)

from openoligo.seq import Seq


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    await Tortoise.init(db_url="sqlite://openoligo.db", modules={"models": ["api.models"]})
    await Tortoise.generate_schemas()


@app.get("/health")
def root():
    return {"status": "ok"}


@app.post("/sequence/")
async def add_sequence(sequence: JobModelIn):
    try:
        await SequenceJob.create(sequence=sequence.sequence)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/sequence/", response_model=list[JobModelOut])
async def get_sequences_list():
    return await SequenceJob.all().limit(100)


@app.get("/sequence/{sequence_id}", response_model=JobModelOut)
async def get_sequence(sequence_id: int):
    sequence = await SequenceJob.get_or_none(id=sequence_id)
    if sequence is None:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return sequence


@app.patch("/sequence/{sequence_id}")
async def update_sequence(sequence_id: int, sequence: str):
    seq = await SequenceJob.get_or_none(id=sequence_id)
    if seq is None:
        raise HTTPException(status_code=404, detail="Sequence not found")
    seq.sequence = sequence
    await seq.save()


@app.get("/status/{instrument_status_id}", response_model=InstrumentStatusModelOut)
async def get_instrument_status(instrument_status_id: int):
    status = await InstrumentStatus.get_or_none(id=instrument_status_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Instrument status not found")
    return status


if __name__ == "__main__":
    uvicorn.run("api.server:app", host="127.0.0.1", port=8000, reload=True)
