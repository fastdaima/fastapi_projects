# reference https://github.com/LAION-AI/Open-Assistant/blob/main/backend/oasst_backend/api/deps.py

from typing import Any
from fastapi.middleware import Middleware
import redis.asyncio as redis
import uvicorn 
from contextlib import asynccontextmanager 
from fastapi import Depends, FastAPI, Request, Response 
from fastapi.middleware.cors import CORSMiddleware

from fastapi_limiter import FastAPILimiter 
from fastapi_limiter.depends import RateLimiter 


class AuthorizationMiddleware: 
    def __init__(self, app) -> None:
        self.app = app 
        
    async def __call__(self, scope, receive, send) -> Any:
        if scope['type'] == 'lifespan':
            print('lifespan')
            # message = await receive()
            # print(message)
        try: 
            request = Request(scope)
            scope['user'] = '1232'
        except Exception as e:
            print(e)
        await self.app(scope, receive, send)


                


def make_middlewares():
    middleware = [
        Middleware( CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],),
    Middleware(AuthorizationMiddleware)
    ]
    return middleware


async def user_identifier(request: Request) -> str:
    """Identify a request by user based on api_key and user header"""
    return request['user']
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    user = request.headers.get("x-oasst-user") 

    if not user:
        payload = await request.json()
        auth_method = payload.get("user").get("auth_method")
        user_id = payload.get("user").get("id")
        user = f"{auth_method}:{user_id}"
    return f"{api_key}:{user}"


class UserRateLimiter(RateLimiter):
    def __init__(
        self, times: int = 100, milliseconds: int = 0, seconds: int = 0, minutes: int = 1, hours: int = 0
    ) -> None:
        super().__init__(times, milliseconds, seconds, minutes, hours, user_identifier)

    async def __call__(self, request: Request, response: Response) -> None:
        # Skip if rate limiting is disabled
        # if not settings.RATE_LIMIT:
        #     return

        # Attempt to retrieve api_key and user information
        # user = (await request.json()).get("user")
        user = request['user']
        print(user)

        # Skip when api_key and user information are not available
        # (such that it will be handled by `APIClientRateLimiter`)
        # if not api_key or not user or not user.get("id"):
        #     return

        return await super().__call__(request, response)



@asynccontextmanager
async def lifespan(_: FastAPI):
    redis_connection = redis.from_url('redis://localhost:6379', encoding='utf-8')
    await FastAPILimiter.init(redis_connection)
    print("redis connection successful")
    yield {'status': "success"}

    await FastAPILimiter.close()


app = FastAPI(lifespan=lifespan, middleware=make_middlewares())
@app.get("/", dependencies=[Depends(UserRateLimiter(times=2, minutes=1))])
async def index(): 
    return {'msg': 'hello srk'}


if __name__ == '__main__':
    uvicorn.run(app)