from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from chain import agent
import asyncio
import json

app = FastAPI(title="FM Assistant", version="1.0.0")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []

class ChatResponse(BaseModel):
    response: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        from chain import run_agent
        response = run_agent(req.message)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def generate():
        history = [m.model_dump() for m in req.history]
        messages = history + [{"role": "user", "content": req.message}]

        final_response = None

        # Собираем все шаги, берём только финальный AIMessage без tool_calls
        for step in agent.stream(
                {"messages": messages},
                stream_mode="values",
        ):
            last = step["messages"][-1]
            if (
                    last.__class__.__name__ == "AIMessage"
                    and last.content
                    and not getattr(last, "tool_calls", None)
            ):
                final_response = last.content

        # Стримим только финальный ответ
        if final_response:
            for char in final_response:
                yield f"data: {json.dumps({'content': char})}\n\n"
                await asyncio.sleep(0.01)

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")