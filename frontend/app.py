import chainlit as cl
import httpx
import json

BACKEND_URL = "http://backend:8000"


@cl.on_chat_start
async def start():
    cl.user_session.set("history", [])
    await cl.Message(
        content="⚽ **Добро пожаловать в Dugout AI!**\n\nЯ помогу найти игроков и дать тактические советы по Football Manager 23. Спрашивайте!"
    ).send()


@cl.on_message
async def main(message: cl.Message):
    history = cl.user_session.get("history", [])

    # Показываем индикатор загрузки
    await cl.Message(content="").send()

    thinking = await cl.Message(content="⏳ Думаю...").send()

    full_response = ""

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
                "POST",
                f"{BACKEND_URL}/chat/stream",
                json={
                    "message": message.content,
                    "history": history
                }
        ) as response:
            first_chunk = True
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        token = chunk.get("content", "")
                        if token:
                            if first_chunk:
                                # Убираем "Думаю..." и начинаем печатать ответ
                                await thinking.remove()
                                msg = cl.Message(content="")
                                await msg.send()
                                first_chunk = False
                            full_response += token
                            await msg.stream_token(token)
                    except Exception:
                        pass

    if not first_chunk:
        await msg.update()

    history.append({"role": "user", "content": message.content})
    history.append({"role": "assistant", "content": full_response})
    cl.user_session.set("history", history)