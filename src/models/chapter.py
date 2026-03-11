from pydantic import BaseModel


class Chapter(BaseModel):
    chapter: int
    title: str
    content: str


class ChapterSummary(BaseModel):
    chapter: int
    title: str
    summary: str
