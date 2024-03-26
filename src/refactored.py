from datetime import datetime
from typing import List, Optional
import uuid
import json

import redis
import chainlit as cl

import chainlit.data as cl_data
from chainlit.data import BaseDataLayer
from chainlit.step import StepDict



now = datetime.utcnow().isoformat()




"""
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
    {
        "id": "test2",
        "createdAt": now,
        "user": user_dict,
        "metadata": {"name": "thread 2"},
        "steps": [
            {
                "id": "test3",
                "createdAt": now,
                "name": "test",
                "type": "user_message",
                "output": "Message 3",
            },
            {
                "id": "test4",
                "createdAt": now,
                "name": "test",
                "type": "assistant_message",
                "output": "Message 4",
            },
        ],
    },
]  # type: List[cl_data.ThreadDict]
deleted_thread_ids = []  # type: List[str]
"""



class RedisDataLayer(BaseDataLayer):
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)

    async def get_user(self, identifier: str):
        serialized_user = self.redis.hget('users', identifier)
        if serialized_user:
            user_data = json.loads(serialized_user)
            return cl.PersistedUser(id=user_data['id'], createdAt=user_data['createdAt'], identifier=identifier)
        return None

    async def create_user(self, user: cl.User):
        user_data = {
            'id': user.identifier,
            'createdAt': datetime.utcnow().isoformat(),
            'identifier': user.identifier
        }
        serialized_user = json.dumps(user_data)
        self.redis.hset('users', user.identifier, serialized_user)
        return cl.PersistedUser(id=user_data['id'], createdAt=user_data['createdAt'], identifier=user.identifier)
 

    async def get_thread_author(self, thread_id: str):
        serialized_thread = self.redis.hget('thread_authors', thread_id)
        if serialized_thread:
            return json.loads(serialized_thread)
        return None


    # @cl_data.queue_until_user_message()
    # async def create_step(self, step_dict):
    #     # Convert step_dict to a string or a suitable format
    #     step_data = ... # serialize step_dict
    #     self.redis.lpush('thread_steps', step_data)


    async def list_threads(self, pagination, filters):
        thread_ids = self.redis.smembers('thread_ids')  # Get all thread IDs
        threads = []

        # Fetch all threads
        for thread_id in thread_ids:
            serialized_thread = self.redis.hget('threads', thread_id)
            if serialized_thread:
                threads.append(json.loads(serialized_thread))

        print(threads)

        # Ignore pagination and filters, return all threads
        return cl_data.PaginatedResponse(
            data=threads,  # All threads
            pageInfo=cl_data.PageInfo(hasNextPage=False, endCursor=None)  # PageInfo with no next page
        )




    def deep_get(self, dictionary, keys):
        """Recursively get a deep value from a dictionary."""
        for key in keys:
            dictionary = dictionary.get(key, {})
        return dictionary if dictionary else None

    def create_page_info(self, total_items, start, end):
        """Create PageInfo object."""
        has_next_page = end < total_items
        has_previous_page = start > 0
        end_cursor = end if has_next_page else None
        start_cursor = start if has_previous_page else None
        return cl_data.PageInfo(
            hasNextPage=has_next_page,
            hasPreviousPage=has_previous_page,
            startCursor=start_cursor,
            endCursor=end_cursor
        )

    # Example function to create PageInfo, you need to implement this based on your pagination logic
    def create_page_info(self, items: List, pagination):
        has_next_page = len(items) > (pagination.offset + pagination.limit) if pagination.limit is not None else False
        end_cursor = pagination.offset + pagination.limit if has_next_page else len(items)
        return cl_data.PageInfo(hasNextPage=has_next_page, endCursor=end_cursor)


    async def get_thread(self, thread_id: str):
        serialized_thread = self.redis.hget('threads', thread_id)
        if serialized_thread:
            return json.loads(serialized_thread)
        return None

    async def delete_thread(self, thread_id: str):
        self.redis.hdel('threads', thread_id)
        self.redis.srem('thread_ids', thread_id)  # Also remove the thread ID from the set of thread IDs

    async def create_or_update_thread(self, thread_id: str, step: dict):
        existing_thread = self.redis.hget('threads', thread_id)
        if existing_thread:
            print("Updating existing thread")
            thread_steps = json.loads(existing_thread)
        else:
            print("Creating new thread")
            thread_steps = []

        thread_steps.append(step)
        self.redis.hset('threads', thread_id, json.dumps(thread_steps))
        self.redis.sadd('thread_ids', thread_id)  # Add the thread ID to the set of thread IDs if it's not already there




cl_data._data_layer = RedisDataLayer()

@cl.on_chat_start
async def on_chat_start():
    # make_one()
    app_user = cl.user_session.get("user")
    print(app_user.__dict__)
    # {'id': 'admin', 'createdAt': '2024-02-19T19:28:11.485746', 'identifier': 'admin', 'metadata': {}}
    await cl.Message(f"Hello {app_user.identifier}").send()


@cl.on_message
async def handle_message(message: cl.Message):
    # user = cl.User(identifier="admin")  # Assuming 'admin' is the default user for simplicity
    user = cl.user_session.get("user")

    thread_id = f"thread_{user.identifier}"
    step = {
        "id": str(uuid.uuid4()),
        "metadata": {"name": "user_message"},
        "createdAt": datetime.utcnow().isoformat(),
        "user": {'identifier': user.identifier, 'metadata': user.metadata},
        "type": "user_message",
        "output": message.content,
    }

    await cl_data._data_layer.create_or_update_thread(thread_id, step)

    # Fetch the existing thread or initialize a new one
    # serialized_thread = cl_data._data_layer.redis.hget('threads', thread_id)
    # if serialized_thread:
    #     thread_steps = json.loads(serialized_thread)
    # else:
    #     thread_steps = []

    # # Append the new step to the thread
    # thread_steps.append(step)
    
    # # Update the thread in Redis
    # cl_data._data_layer.redis.hset('threads', thread_id, json.dumps(thread_steps))
    # cl_data._data_layer.redis.sadd('thread_ids', thread_id)  # Ensure the thread ID is tracked


    async with cl.Step(root=True, disable_feedback=True) as step:
        step.output = "Thinking..."
    await cl.Message("Ok!").send()


@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
    if (username, password) == ("admin", "admin"):
        return cl.User(identifier="admin")
    else:
        return None


@cl.on_chat_resume
async def on_chat_resume(thread: cl_data.ThreadDict):
    await cl.Message(f"Welcome back to {thread['metadata']['name']}").send()



def make_one():

    # Example thread structure
    thread = {
        "id": "test1",
        "metadata": {"name": "thread 1"},
        "createdAt": str(datetime.utcnow().isoformat()),
        "user": cl.user_session.get("user").to_dict(),  # Make sure user_dict is properly structured
        "steps": [
            {
                "id": "step1",
                "name": "User Message",
                "createdAt": str(datetime.utcnow().isoformat()),
                "type": "user_message",
                "output": "Message 1",
            },
            {
                "id": "step2",
                "name": "Assistant Message",
                "createdAt": str(datetime.utcnow().isoformat()),
                "type": "assistant_message",
                "output": "Message 2",
            },
        ],
    }

    # Serialize the thread object to a JSON string
    serialized_thread = json.dumps(thread)

    # Store the serialized thread in Redis
    cl_data._data_layer.redis.hset('threads', thread['id'], serialized_thread)