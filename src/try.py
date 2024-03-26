from datetime import datetime
from typing import List, Optional
import json
import random

import redis
import chainlit as cl

import chainlit.data as cl_data
from chainlit.data import BaseDataLayer
from chainlit.step import StepDict


now = datetime.utcnow().isoformat()

user_dict = {"id": "test", "createdAt": now, "identifier": "admin"}

thread_history = [
    {
        "id": "test1",
        "metadata": {"name": "thread 1"},
        "createdAt": now,
        "user": user_dict,
        "steps": [
            {
                "id": "test1",
                "name": "test",
                "createdAt": now,
                "type": "user_message",
                "output": "Message 1",
            },
            {
                "id": "test2",
                "name": "test",
                "createdAt": now,
                "type": "assistant_message",
                "output": "Message 2",
            },
        ],
    },
]  # type: List[cl_data.ThreadDict]
deleted_thread_ids = []  # type: List[str]




class TestDataLayer(BaseDataLayer):
    async def get_user(self, identifier: str):
        return cl.PersistedUser(id="test", createdAt=now, identifier=identifier)

    async def create_user(self, user: cl.User):
        return cl.PersistedUser(id="test", createdAt=now, identifier=user.identifier)


    async def get_thread_author(self, thread_id: str):
        return "admin"


    async def list_threads(
        self, pagination: cl_data.Pagination, filter: cl_data.ThreadFilter
    ) -> cl_data.PaginatedResponse[cl_data.ThreadDict]:
        # global thread_history
        return cl_data.PaginatedResponse(
            data=[t for t in thread_history if t["id"] not in deleted_thread_ids],
            pageInfo=cl_data.PageInfo(hasNextPage=False, endCursor=None),
        )

    async def get_thread(self, thread_id: str):
        # global thread_history
        return next((t for t in thread_history if t["id"] == thread_id), None)

    async def delete_thread(self, thread_id: str):
        deleted_thread_ids.append(thread_id)


cl_data._data_layer = TestDataLayer()


@cl.on_chat_start
async def main():
    await cl.Message("Ready!", disable_feedback=True).send()

    # append the first message to the thread history
    # global thread_history
    thread_history.append(
        {
        "id": f"test{random.randint(0, 1000)}",
        "metadata": {"name": "thread 999"},
        "createdAt": now,
        "user": user_dict,
        "steps": [
            {
                "id": "test123",
                "name": "test",
                "createdAt": now,
                "type": "user_message",
                "output": "Message 999",
            }
        ],
    }
    )

@cl.author_rename
def author_rename(author: str) -> str:
    return "Echobot"


@cl.on_message
async def handle_message(message):
    # Wait for queue to be flushed
    await cl.sleep(0.2)

    # Append user message to the thread history
    # global thread_history
    thread_history[-1]["steps"].append(
        {
            "id": "test",
            "createdAt": now,
            "name": "test",
            "type": "user_message",
            "output": message.content,
        }
    )

    print(json.dumps(thread_history, indent=4))
    # await cl.Message(message.content).send()
    await cl.Message(json.dumps(thread_history, indent=4)).send()


@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
    if (username, password) == ("admin", "admin"):
        return cl.User(identifier="admin")
    else:
        return None


@cl.on_chat_resume
async def on_chat_resume(thread: cl_data.ThreadDict):
    await cl.Message(f"Welcome back to {thread['metadata']['name']}").send()
    
