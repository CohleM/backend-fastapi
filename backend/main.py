from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

# from websocket_manager import WebSocketManager
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
import time
from typing import AsyncGenerator, NoReturn

from .websocket_manager import WebSocketManager
from datetime import datetime, timedelta

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from passlib.context import CryptContext
from pydantic import BaseModel
import requests
import json


##db
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session

from . import crud, models, schemas

from .database import SessionLocal, engine

from .routers import users, authentication, drafts, files
import sys

sys.path.append("/Users/cohlem/projects/FastAPI/backend-fastapi/researcher")

from researcher.core.agent import Researcher


models.Base.metadata.create_all(bind=engine)


# Initials
manager = WebSocketManager()
app = FastAPI()
client = AsyncOpenAI()


app.include_router(users.router)
app.include_router(authentication.router)
app.include_router(drafts.router)
app.include_router(files.router)


# Add this before defining your FastAPI app
origins = [
    "http://localhost",
    "http://localhost:3000",
]

# Add this to your FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# with open("index.html") as f:
#     html = f.read()


# # to get a string like this run:
# # openssl rand -hex 32
# SECRET_KEY = "your-secret-key"  # Change this to a secure random key
# ALGORITHM = "HS256"


# fake_users_db = {
#     "johndoe": {
#         "username": "johndoe",
#         "full_name": "John Doe",
#         "email": "iamafanaticus@gmail.com",
#         "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
#         "disabled": False,
#     }
# }


# class User(BaseModel):
#     email: str


# def create_magic_link_token(data: dict):
#     return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


# @app.get("/token/{token}")
# def verify_magic_link_token(token: str):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         return {"payload": payload, "message": "successfully loggedIn"}

#     except JWTError:
#         return {"payload": "not-found"}


# @app.post("/magic-link/")
# def send_magic_link(user: User):
#     # Generate a unique token
#     token = create_magic_link_token({"sub": user.email})

#     # Send the token via email (replace with your email sending logic)
#     send_email(
#         user.email,
#         "Log into OkProfessor",
#         f"Click on this link to authenticate: http://127.0.0.1:8000/token/{token}",
#     )
#     return {"message": f"Magic link sent to your {user.email}"}


# def send_email(to_email: str, subject: str, text_content: str):
#     url = "https://api.brevo.com/v3/smtp/email"
#     payload = json.dumps(
#         {
#             "sender": {"name": "Manish", "email": "manisrocker@gmail.com"},
#             "to": [{"email": f"{to_email}"}],
#             "subject": subject,
#             "textContent": text_content,
#         }
#     )
#     headers = {
#         "accept": "application/json",
#         "api-key": "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",
#         "content-type": "application/json",
#     }
#     response = requests.request("POST", url, headers=headers, data=payload)
#     print(response.text)


## Websocket connection and streaming openai response
async def get_ai_response(message: str) -> AsyncGenerator[str, None]:
    """
    OpenAI Response
    """
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant, skilled in explaining "
                    "complex concepts in simple terms."
                ),
            },
            {
                "role": "user",
                "content": message,
            },
        ],
        stream=True,
    )

    all_content = ""
    async for chunk in response:
        content = chunk.choices[0].delta.content
        finish_reason = chunk.choices[0].finish_reason
        # print("haha", content)
        print(content)
        # if content:
        # all_content += content
        if content:
            all_content += content
        yield all_content, finish_reason


# @app.get("/")
# async def web_app() -> HTMLResponse:
#     """
#     Web App
#     """
#     return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> NoReturn:
    """
    Websocket for AI responses
    """

    await manager.connect(websocket)

    while True:
        message = await websocket.receive_json() # message has type { 'text' : text, 'allAIOptions' : allAIOptions}
        # allAIOptions has type type AIOptionsType = { AICommands : string, webSearch : boolean }
        print("message printing from backend", message['allAIOptions'], type(message))
        query = message['text']
        options = message['allAIOptions']

        if options['AICommands'] == '1' and options['webSearch'] == True: # 1 belongs to generate report
            result = Researcher(query,websocket).run_researcher_agent()
        elif options['AICommands'] == '2' and options['webSearch'] == True: # 2 belongs to generate QA
            result = Researcher(query,websocket).run_qa_agent()
        elif options['AICommands'] == '3' and options['webSearch'] == False: # 3 belongs to Summarization 
            result = Researcher(query,websocket).run_summarization_agent()
        elif options['AICommands'] == '4' and options['webSearch'] == False: # 4 belongs to generate Paraphrase
            result = Researcher(query,websocket).run_paraphrasing_agent()
 




        # async for text, finish_reason in get_ai_response(message):
        # async for text, finish_reason in Researcher(message,websocket).run_researcher_agent():
        # async for text, finish_reason in Researcher(message).run_qa_agent():
        # async for text, finish_reason in Researcher(message).run_summarization_agent():
        async for text, finish_reason in result:
            # print(text, finish_reason)
            await websocket.send_json({"content": text, "finish_reason": finish_reason})


# ### testing database
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# @app.post("/users/", response_model=schemas.User)
# def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
#     db_user = crud.get_user_by_email(db, email=user.email)
#     if db_user:
#         raise HTTPException(status_code=400, detail="Email already registered")
#     return crud.create_user(db=db, user=user)


# @app.get("/users/", response_model=list[schemas.User])
# def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     users = crud.get_users(db, skip=skip, limit=limit)
#     return users


# @app.get("/users/{user_id}", response_model=schemas.User)
# def read_user(user_id: int, db: Session = Depends(get_db)):
#     db_user = crud.get_user(db, user_id=user_id)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user


# @app.post("/users/{user_id}/items/", response_model=schemas.Item)
# def create_item_for_user(
#     user_id: int, item: schemas.ItemCreate, db: Session = Depends(get_db)
# ):
#     return crud.create_user_item(db=db, item=item, user_id=user_id)


# @app.get("/items/", response_model=list[schemas.Item])
# def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     items = crud.get_items(db, skip=skip, limit=limit)
#     return items
