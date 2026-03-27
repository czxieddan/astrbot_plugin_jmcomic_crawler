from __future__ import annotations

from pathlib import Path

from managers.cache_manager import CacheManager
from managers.config_state_manager import ConfigStateManager
from managers.memory_manager import MemoryManager
from managers.scheduler_manager import SchedulerManager
from managers.task_manager import TaskManager
from services.action_handler import ActionHandler
from services.comment_service import CommentService
from services.command_router import CommandRouter
from services.config_service import ConfigService
from services.context_memory_service import ContextMemoryService
from services.dependency_service import DependencyService
from services.download_service import DownloadService
from services.jm_service import JMComicService
from services.llm_response_service import LLMResponseService
from services.permission_service import PermissionService
from services.pool_service import PoolService
from services.public_api_service import PublicAPIService
from services.recommend_service import RecommendService
from services.response_builder import ResponseBuilder
from services.sentiment_service import SentimentService
from services.summary_service import SummaryService
from services.tool_executor import ToolExecutor
from services.usecases.query_usecase import QueryUseCase
from services.usecases.recommend_usecase import RecommendUseCase
from services.usecases.summary_usecase import SummaryUseCase
from services.usecases.task_usecase import TaskUseCase
from services.workflow_service import WorkflowService


class PluginApplication:
    def __init__(self, config: dict, context):
        self.config_service = ConfigService(config)
        self.config = self.config_service.get_config()
        self.context = context

        data_dir = Path("data")
        data_dir.mkdir(parents=True, exist_ok=True)

        self.dependency_service = DependencyService(
            project_root=".",
            data_dir=str(data_dir),
            auto_install=bool(self.config.get("auto_install_dependencies", True)),
            check_on_startup=bool(self.config.get("dependency_check_on_startup", True)),
            timeout_seconds=int(self.config.get("dependency_install_timeout_seconds", 300) or 300),
        )
        self.dependency_service.ensure_dependencies()

        self.cache_manager = CacheManager(
            str(data_dir / "cache"),
            enabled=bool(self.config.get("cache_enabled", True)),
        )
        self.memory_manager = MemoryManager(
            str(data_dir / "memory"),
            enabled=bool(self.config.get("memory_enabled", True)),
            ttl_seconds=int(self.config.get("memory_ttl_seconds", 3600) or 3600),
        )
        self.scheduler_manager = SchedulerManager(
            max_concurrency=int(self.config.get("max_concurrent_downloads", 2) or 2),
        )
        self.config_state_manager = ConfigStateManager(str(data_dir / "config"))
        self.pool_service = PoolService(self.config, self.config_state_manager)

        self.service = JMComicService(self.config, self.pool_service)
        self.task_manager = TaskManager(str(data_dir))
        self.download_service = DownloadService(
            self.config,
            self.service,
            self.task_manager,
            self.scheduler_manager,
        )
        self.comment_service = CommentService(self.config, self.service)
        self.summary_service = SummaryService(self.config)
        self.recommend_service = RecommendService(self.config)
        self.sentiment_service = SentimentService(self.config)
        self.llm_response_service = LLMResponseService(self.config, context)
        self.permission_service = PermissionService(self.config)
        self.response_builder = ResponseBuilder()
        self.memory_service = ContextMemoryService(self.memory_manager)

        self.query_usecase = QueryUseCase(
            jm_service=self.service,
            comment_service=self.comment_service,
            sentiment_service=self.sentiment_service,
            response_builder=self.response_builder,
            llm_response_service=self.llm_response_service,
            cache_manager=self.cache_manager,
            memory_service=self.memory_service,
        )
        self.summary_usecase = SummaryUseCase(
            query_usecase=self.query_usecase,
            summary_service=self.summary_service,
            response_builder=self.response_builder,
            llm_response_service=self.llm_response_service,
            sentiment_service=self.sentiment_service,
        )
        self.recommend_usecase = RecommendUseCase(
            query_usecase=self.query_usecase,
            recommend_service=self.recommend_service,
            response_builder=self.response_builder,
            llm_response_service=self.llm_response_service,
            sentiment_service=self.sentiment_service,
        )
        self.task_usecase = TaskUseCase(
            query_usecase=self.query_usecase,
            download_service=self.download_service,
            task_manager=self.task_manager,
            response_builder=self.response_builder,
            llm_response_service=self.llm_response_service,
            memory_service=self.memory_service,
        )

        self.action_handler = ActionHandler(
            query_usecase=self.query_usecase,
            summary_usecase=self.summary_usecase,
            recommend_usecase=self.recommend_usecase,
            task_usecase=self.task_usecase,
        )
        self.workflow_service = WorkflowService(self.action_handler, self.memory_service)
        self.tool_executor = ToolExecutor(self)
        self.public_api_service = PublicAPIService(self)
        self.command_router = CommandRouter(self)

    async def close(self):
        await self.service.close()