"""Root discovery bridge for tests owned by first-class packages."""

from plugins.platforms.notion.tests.test_comment_adapter import (  # noqa: F401
    NotionCommentAdapterTests,
)
from plugins.platforms.notion.tests.test_webhook_protocol import (  # noqa: F401
    NotionWebhookProtocolTests,
)
from plugins.platforms.notion.tests.test_setup_credentials import (  # noqa: F401
    NotionSetupCredentialTests,
)
from apps.installer.tests.test_architecture import SetupArchitectureTests  # noqa: F401
from apps.installer.tests.test_composio_connection import (  # noqa: F401
    ComposioConnectionTests,
)
from apps.installer.tests.test_connections import SetupCertifyUXTests  # noqa: F401
from apps.installer.tests.test_e2e import RealDockerSetupE2E  # noqa: F401
from apps.installer.tests.test_init import SetupInitTests  # noqa: F401
from apps.installer.tests.test_launch import SetupLaunchTests  # noqa: F401
from apps.installer.tests.test_messaging_live import LiveTelegramMessagingTest  # noqa: F401
from apps.installer.tests.test_profile import SetupProfileTests  # noqa: F401
from apps.installer.tests.test_runtime import SetupRuntimeTests  # noqa: F401
from apps.installer.tests.test_workspace import SetupWorkspaceTests  # noqa: F401
from apps.eval_viewer.tests.test_viewer import EvidenceViewerTests  # noqa: F401
from apps.doctor.tests.test_run import CompanyDoctorTests  # noqa: F401
from apps.doctor.tests.test_evaluation import EvaluationRunnerTests  # noqa: F401
from apps.installer.tests.test_composio_session import ComposioSessionTests  # noqa: F401
from apps.installer.tests.test_model_output import ModelOutputTests  # noqa: F401
from apps.installer.tests.test_connection_evals import ConnectionEvalTests  # noqa: F401
from apps.installer.tests.test_readiness_evals import ReadinessEvalTests  # noqa: F401
from apps.installer.tests.test_provider_catalog import ProviderCatalogTests  # noqa: F401
from apps.installer.tests.test_workspace_schema import WorkspaceSchemaTests  # noqa: F401
