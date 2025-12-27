import asyncio
from typing import Callable, Any, Dict
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


@dataclass
class RetryTask:
    task_id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    max_retries: int = 5
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


class RetryQueue:
    def __init__(self, retry_interval: float = 30.0):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.tasks: Dict[str, RetryTask] = {}
        self.retry_interval = retry_interval
        self.is_running = False

    async def add_task(self, func: Callable, *args, **kwargs) -> str:
        task_id = str(uuid.uuid4())
        task = RetryTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs
        )
        self.tasks[task_id] = task
        await self.queue.put(task_id)
        logger.info(f"Added task {task_id} to retry queue")
        return task_id

    async def process_queue(self):
        self.is_running = True
        logger.info("Retry queue processor started")

        while self.is_running:
            try:
                task_id = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=self.retry_interval
                )

                if task_id not in self.tasks:
                    continue

                task = self.tasks[task_id]

                try:
                    if asyncio.iscoroutinefunction(task.func):
                        await task.func(*task.args, **task.kwargs)
                    else:
                        task.func(*task.args, **task.kwargs)

                    logger.info(f"Task {task_id} completed successfully")
                    del self.tasks[task_id]

                except Exception as e:
                    task.retry_count += 1
                    logger.warning(
                        f"Task {task_id} failed (attempt {task.retry_count}/{task.max_retries}): {str(e)}"
                    )

                    if task.retry_count < task.max_retries:
                        await asyncio.sleep(self.retry_interval)
                        await self.queue.put(task_id)
                    else:
                        logger.error(f"Task {task_id} failed after {task.max_retries} attempts")
                        del self.tasks[task_id]

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing retry queue: {str(e)}")

    async def start(self):
        if not self.is_running:
            asyncio.create_task(self.process_queue())

    async def stop(self):
        self.is_running = False

    def get_queue_status(self) -> dict:
        return {
            "queue_size": self.queue.qsize(),
            "total_tasks": len(self.tasks),
            "tasks": [
                {
                    "task_id": task.task_id,
                    "retry_count": task.retry_count,
                    "max_retries": task.max_retries,
                    "created_at": task.created_at.isoformat()
                }
                for task in self.tasks.values()
            ]
        }


retry_queue = RetryQueue()
