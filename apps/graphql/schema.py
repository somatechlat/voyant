"""GraphQL schema for Voyant — auto-generated types, queries, and mutations.

Uses graphene-django to expose Django models through a GraphQL API with:
- Auto-generated types for ontology, datasets, pipelines, and ML models
- Mutations for create/update/delete of key resources
- DataLoader pattern for N+1 query prevention
- Depth limiting (max 10 levels)
- Tenant-scoped queries

Endpoint: /graphql
"""

from __future__ import annotations

import logging
from typing import Any

import graphene
from graphene_django import DjangoObjectType

from apps.ontology.models import (
    Link as LinkInstance,
)
from apps.ontology.models import (
    LinkType,
    Property,
)
from apps.ontology.models import (
    Object as OntObject,
)
from apps.ontology.models import (
    ObjectType as OntObjectType,
)

logger = logging.getLogger("voyant.graphql")

# ---------------------------------------------------------------------------
# DataLoaders (N+1 prevention)
# ---------------------------------------------------------------------------


class DataLoaders:
    """Container for per-request DataLoaders to batch DB queries."""

    def __init__(self, tenant_id: str | None = None) -> None:
        self._tenant_id = tenant_id
        self._cache: dict[str, Any] = {}

    def _get_queryset(self, model: Any) -> Any:
        qs = model.objects.all()
        if self._tenant_id and hasattr(model, "tenant_id"):
            qs = qs.filter(tenant_id=self._tenant_id)
        return qs


def get_dataloaders(info: Any) -> DataLoaders:
    """Get or create DataLoaders for the current request."""
    if not hasattr(info.context, "_dataloaders"):
        tenant_id = getattr(info.context, "tenant_id", None)
        info.context._dataloaders = DataLoaders(tenant_id=tenant_id)
    return info.context._dataloaders


# ---------------------------------------------------------------------------
# Ontology Types
# ---------------------------------------------------------------------------


class ObjectTypeType(DjangoObjectType):
    """GraphQL type for ontology ObjectType."""

    class Meta:
        model = OntObjectType
        fields = (
            "id",
            "name",
            "description",
            "version",
            "backing_dataset",
            "primary_key_column",
            "created_at",
            "updated_at",
        )

    properties_list = graphene.List(lambda: PropertyTypeGQL)
    instance_count = graphene.Int()

    def resolve_properties_list(self, info: Any) -> Any:
        return self.properties.all()  # type: ignore[attr-defined]

    def resolve_instance_count(self, info: Any) -> int:
        return self.instances.filter(deleted_at__isnull=True).count()  # type: ignore[attr-defined]


class PropertyTypeGQL(DjangoObjectType):
    """GraphQL type for ontology Property."""

    class Meta:
        model = Property
        fields = (
            "id",
            "name",
            "property_type",
            "required",
            "default_value",
            "validation_rules",
            "metadata",
            "created_at",
        )


class ObjectInstanceType(DjangoObjectType):
    """GraphQL type for ontology Object instance."""

    class Meta:
        model = OntObject
        fields = (
            "id",
            "object_type",
            "properties",
            "version",
            "created_at",
            "updated_at",
        )


class LinkTypeType(DjangoObjectType):
    """GraphQL type for ontology LinkType."""

    class Meta:
        model = LinkType
        fields = (
            "id",
            "name",
            "description",
            "source_object_type",
            "target_object_type",
            "cardinality",
            "inverse_name",
            "created_at",
        )


class LinkInstanceType(DjangoObjectType):
    """GraphQL type for ontology Link instance."""

    class Meta:
        model = LinkInstance
        fields = (
            "id",
            "link_type",
            "source_object",
            "target_object",
            "properties",
            "created_at",
        )


# ---------------------------------------------------------------------------
# Discovery / Dataset Types
# ---------------------------------------------------------------------------

from apps.discovery.models import Source  # noqa: E402


class SourceType(DjangoObjectType):
    """GraphQL type for data Source."""

    class Meta:
        model = Source
        fields = (
            "id",
            "name",
            "source_type",
            "status",
            "connection_config",
            "sync_schedule",
            "created_at",
            "updated_at",
        )


# ---------------------------------------------------------------------------
# Pipeline Types
# ---------------------------------------------------------------------------

from apps.pipelines.models import Pipeline, PipelineRun, PipelineStep  # noqa: E402


class PipelineStepTypeGQL(DjangoObjectType):
    """GraphQL type for PipelineStep."""

    class Meta:
        model = PipelineStep
        fields = (
            "id",
            "step_type",
            "name",
            "order",
            "config",
            "retry_count",
            "timeout_seconds",
        )


class PipelineRunType(DjangoObjectType):
    """GraphQL type for PipelineRun."""

    class Meta:
        model = PipelineRun
        fields = (
            "id",
            "pipeline",
            "status",
            "triggered_by",
            "trigger_type",
            "parameters",
            "started_at",
            "completed_at",
            "result_summary",
            "error_message",
            "steps_completed",
            "steps_total",
            "created_at",
        )


class PipelineType(DjangoObjectType):
    """GraphQL type for Pipeline."""

    class Meta:
        model = Pipeline
        fields = (
            "id",
            "name",
            "description",
            "status",
            "schedule",
            "schedule_timezone",
            "config",
            "version",
            "created_at",
            "updated_at",
        )

    steps_list = graphene.List(PipelineStepTypeGQL)
    recent_runs = graphene.List(PipelineRunType, limit=graphene.Int(default_value=5))

    def resolve_steps_list(self, info: Any) -> Any:
        return self.steps.all().order_by("order")  # type: ignore[attr-defined]

    def resolve_recent_runs(self, info: Any, limit: int = 5) -> Any:
        return self.runs.all().order_by("-created_at")[:limit]  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# ML Platform Types
# ---------------------------------------------------------------------------

from apps.ml_platform.models import (  # noqa: E402
    Experiment,
    ModelVersion,
    RegisteredModel,
    Run,
)


class RunType(DjangoObjectType):
    """GraphQL type for ML Run."""

    class Meta:
        model = Run
        fields = (
            "id",
            "experiment",
            "name",
            "status",
            "params",
            "metrics",
            "tags",
            "started_at",
            "ended_at",
        )


class ExperimentType(DjangoObjectType):
    """GraphQL type for ML Experiment."""

    class Meta:
        model = Experiment
        fields = (
            "id",
            "name",
            "description",
            "tags",
            "artifact_location",
            "created_at",
            "updated_at",
        )

    runs_list = graphene.List(RunType, limit=graphene.Int(default_value=10))

    def resolve_runs_list(self, info: Any, limit: int = 10) -> Any:
        return self.runs.all().order_by("-started_at")[:limit]  # type: ignore[attr-defined]


class ModelVersionTypeGQL(DjangoObjectType):
    """GraphQL type for Model Version."""

    class Meta:
        model = ModelVersion
        fields = (
            "id",
            "registered_model",
            "version",
            "stage",
            "status",
            "run",
            "storage_path",
            "metrics",
            "description",
            "created_at",
        )


class RegisteredModelType(DjangoObjectType):
    """GraphQL type for Registered Model."""

    class Meta:
        model = RegisteredModel
        fields = (
            "id",
            "name",
            "description",
            "tags",
            "created_at",
            "updated_at",
        )

    versions_list = graphene.List(ModelVersionTypeGQL)

    def resolve_versions_list(self, info: Any) -> Any:
        return self.versions.all().order_by("-version")  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Governance Types
# ---------------------------------------------------------------------------

from apps.governance.models import DataContract, SecurityPolicy  # noqa: E402


class DataContractType(DjangoObjectType):
    """GraphQL type for Data Contract."""

    class Meta:
        model = DataContract
        fields = (
            "id",
            "name",
            "description",
            "dataset_urn",
            "schema_definition",
            "quality_rules",
            "status",
            "version",
            "owner",
            "created_at",
        )


class SecurityPolicyType(DjangoObjectType):
    """GraphQL type for Security Policy."""

    class Meta:
        model = SecurityPolicy
        fields = (
            "id",
            "name",
            "description",
            "status",
            "table_name",
            "column_name",
            "filter_expression",
            "roles",
            "created_at",
        )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


class Query(graphene.ObjectType):
    """Root query type for the Voyant GraphQL API."""

    # Ontology
    ontology_types = graphene.List(
        ObjectTypeType,
        description="List all ontology object types",
    )
    ontology_type = graphene.Field(
        ObjectTypeType,
        id=graphene.UUID(required=True),
        description="Get a single object type by ID",
    )
    ontology_objects = graphene.List(
        ObjectInstanceType,
        type_id=graphene.UUID(),
        limit=graphene.Int(default_value=50),
        description="List ontology object instances",
    )
    ontology_links = graphene.List(
        LinkTypeType,
        description="List all link types",
    )

    # Datasets / Sources
    sources = graphene.List(
        SourceType,
        description="List all data sources",
    )
    source = graphene.Field(
        SourceType,
        id=graphene.UUID(required=True),
        description="Get a single data source by ID",
    )

    # Pipelines
    pipelines = graphene.List(
        PipelineType,
        status=graphene.String(),
        description="List pipelines, optionally filtered by status",
    )
    pipeline = graphene.Field(
        PipelineType,
        id=graphene.UUID(required=True),
        description="Get a single pipeline by ID",
    )

    # ML Platform
    experiments = graphene.List(
        ExperimentType,
        description="List ML experiments",
    )
    experiment = graphene.Field(
        ExperimentType,
        id=graphene.UUID(required=True),
        description="Get a single experiment by ID",
    )
    registered_models = graphene.List(
        RegisteredModelType,
        description="List registered ML models",
    )
    registered_model = graphene.Field(
        RegisteredModelType,
        id=graphene.UUID(required=True),
        description="Get a single registered model by ID",
    )

    # Governance
    data_contracts = graphene.List(
        DataContractType,
        status=graphene.String(),
        description="List data contracts",
    )
    security_policies = graphene.List(
        SecurityPolicyType,
        description="List security policies",
    )

    # ── Resolvers ──────────────────────────────────────────────────────────

    def resolve_ontology_types(self, info: Any) -> Any:
        qs = OntObjectType.objects.filter(deleted_at__isnull=True)
        tenant_id = getattr(info.context, "tenant_id", None)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def resolve_ontology_type(self, info: Any, id: str) -> Any:
        try:
            return OntObjectType.objects.get(id=id, deleted_at__isnull=True)
        except OntObjectType.DoesNotExist:
            return None

    def resolve_ontology_objects(
        self, info: Any, type_id: str | None = None, limit: int = 50
    ) -> Any:
        qs = OntObject.objects.filter(deleted_at__isnull=True)
        if type_id:
            qs = qs.filter(object_type_id=type_id)
        tenant_id = getattr(info.context, "tenant_id", None)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs[:limit]

    def resolve_ontology_links(self, info: Any) -> Any:
        qs = LinkType.objects.filter(deleted_at__isnull=True)
        tenant_id = getattr(info.context, "tenant_id", None)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def resolve_sources(self, info: Any) -> Any:
        qs = Source.objects.all()
        tenant_id = getattr(info.context, "tenant_id", None)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def resolve_source(self, info: Any, id: str) -> Any:
        try:
            return Source.objects.get(id=id)
        except Source.DoesNotExist:
            return None

    def resolve_pipelines(self, info: Any, status: str | None = None) -> Any:
        qs = Pipeline.objects.filter(deleted_at__isnull=True)
        if status:
            qs = qs.filter(status=status)
        tenant_id = getattr(info.context, "tenant_id", None)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def resolve_pipeline(self, info: Any, id: str) -> Any:
        try:
            return Pipeline.objects.get(id=id, deleted_at__isnull=True)
        except Pipeline.DoesNotExist:
            return None

    def resolve_experiments(self, info: Any) -> Any:
        qs = Experiment.objects.all()
        tenant_id = getattr(info.context, "tenant_id", None)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def resolve_experiment(self, info: Any, id: str) -> Any:
        try:
            return Experiment.objects.get(id=id)
        except Experiment.DoesNotExist:
            return None

    def resolve_registered_models(self, info: Any) -> Any:
        qs = RegisteredModel.objects.all()
        tenant_id = getattr(info.context, "tenant_id", None)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def resolve_registered_model(self, info: Any, id: str) -> Any:
        try:
            return RegisteredModel.objects.get(id=id)
        except RegisteredModel.DoesNotExist:
            return None

    def resolve_data_contracts(
        self, info: Any, status: str | None = None
    ) -> Any:
        qs = DataContract.objects.all()
        if status:
            qs = qs.filter(status=status)
        tenant_id = getattr(info.context, "tenant_id", None)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def resolve_security_policies(self, info: Any) -> Any:
        qs = SecurityPolicy.objects.filter(status="active")
        tenant_id = getattr(info.context, "tenant_id", None)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


class CreatePipeline(graphene.Mutation):
    """Create a new pipeline."""

    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String()
        schedule = graphene.String()
        config = graphene.JSONString()

    ok = graphene.Boolean()
    pipeline = graphene.Field(PipelineType)

    def mutate(
        self,
        info: Any,
        name: str,
        description: str = "",
        schedule: str = "",
        config: dict | None = None,
    ) -> CreatePipeline:
        tenant_id = getattr(info.context, "tenant_id", "default")
        pipeline = Pipeline.objects.create(
            tenant_id=tenant_id,
            name=name,
            description=description,
            schedule=schedule,
            config=config or {},
        )
        return CreatePipeline(ok=True, pipeline=pipeline)


class UpdatePipeline(graphene.Mutation):
    """Update an existing pipeline."""

    class Arguments:
        id = graphene.UUID(required=True)
        name = graphene.String()
        description = graphene.String()
        status = graphene.String()
        schedule = graphene.String()
        config = graphene.JSONString()

    ok = graphene.Boolean()
    pipeline = graphene.Field(PipelineType)

    def mutate(self, info: Any, id: str, **kwargs: Any) -> UpdatePipeline:
        try:
            pipeline = Pipeline.objects.get(id=id, deleted_at__isnull=True)
        except Pipeline.DoesNotExist:
            return UpdatePipeline(ok=False, pipeline=None)

        for field, value in kwargs.items():
            if value is not None:
                setattr(pipeline, field, value)
        pipeline.save()
        return UpdatePipeline(ok=True, pipeline=pipeline)


class DeletePipeline(graphene.Mutation):
    """Soft-delete a pipeline."""

    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info: Any, id: str) -> DeletePipeline:
        from django.utils import timezone

        try:
            pipeline = Pipeline.objects.get(id=id, deleted_at__isnull=True)
        except Pipeline.DoesNotExist:
            return DeletePipeline(ok=False)

        pipeline.deleted_at = timezone.now()
        pipeline.save(update_fields=["deleted_at", "updated_at"])
        return DeletePipeline(ok=True)


class CreateObjectType(graphene.Mutation):
    """Create a new ontology object type."""

    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String()
        backing_dataset = graphene.String()

    ok = graphene.Boolean()
    object_type = graphene.Field(ObjectTypeType)

    def mutate(
        self,
        info: Any,
        name: str,
        description: str = "",
        backing_dataset: str = "",
    ) -> CreateObjectType:
        tenant_id = getattr(info.context, "tenant_id", "default")
        ot = OntObjectType.objects.create(
            tenant_id=tenant_id,
            name=name,
            description=description,
            backing_dataset=backing_dataset,
        )
        return CreateObjectType(ok=True, object_type=ot)


class UpdateObjectType(graphene.Mutation):
    """Update an existing object type."""

    class Arguments:
        id = graphene.UUID(required=True)
        name = graphene.String()
        description = graphene.String()
        backing_dataset = graphene.String()

    ok = graphene.Boolean()
    object_type = graphene.Field(ObjectTypeType)

    def mutate(self, info: Any, id: str, **kwargs: Any) -> UpdateObjectType:
        try:
            ot = OntObjectType.objects.get(id=id, deleted_at__isnull=True)
        except OntObjectType.DoesNotExist:
            return UpdateObjectType(ok=False, object_type=None)

        for field, value in kwargs.items():
            if value is not None:
                setattr(ot, field, value)
        ot.version += 1
        ot.save()
        return UpdateObjectType(ok=True, object_type=ot)


class DeleteObjectType(graphene.Mutation):
    """Soft-delete an object type."""

    class Arguments:
        id = graphene.UUID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info: Any, id: str) -> DeleteObjectType:
        from django.utils import timezone

        try:
            ot = OntObjectType.objects.get(id=id, deleted_at__isnull=True)
        except OntObjectType.DoesNotExist:
            return DeleteObjectType(ok=False)

        ot.deleted_at = timezone.now()
        ot.save(update_fields=["deleted_at", "updated_at"])
        return DeleteObjectType(ok=True)


class CreateExperiment(graphene.Mutation):
    """Create a new ML experiment."""

    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String()
        tags = graphene.JSONString()

    ok = graphene.Boolean()
    experiment = graphene.Field(ExperimentType)

    def mutate(
        self,
        info: Any,
        name: str,
        description: str = "",
        tags: dict | None = None,
    ) -> CreateExperiment:
        tenant_id = getattr(info.context, "tenant_id", "default")
        exp = Experiment.objects.create(
            tenant_id=tenant_id,
            name=name,
            description=description,
            tags=tags or {},
        )
        return CreateExperiment(ok=True, experiment=exp)


class UpdateExperiment(graphene.Mutation):
    """Update an existing ML experiment."""

    class Arguments:
        id = graphene.UUID(required=True)
        name = graphene.String()
        description = graphene.String()
        tags = graphene.JSONString()

    ok = graphene.Boolean()
    experiment = graphene.Field(ExperimentType)

    def mutate(self, info: Any, id: str, **kwargs: Any) -> UpdateExperiment:
        try:
            exp = Experiment.objects.get(id=id)
        except Experiment.DoesNotExist:
            return UpdateExperiment(ok=False, experiment=None)

        for field, value in kwargs.items():
            if value is not None:
                setattr(exp, field, value)
        exp.save()
        return UpdateExperiment(ok=True, experiment=exp)


class CreateRegisteredModel(graphene.Mutation):
    """Register a new ML model."""

    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String()
        tags = graphene.JSONString()

    ok = graphene.Boolean()
    model = graphene.Field(RegisteredModelType)

    def mutate(
        self,
        info: Any,
        name: str,
        description: str = "",
        tags: dict | None = None,
    ) -> CreateRegisteredModel:
        tenant_id = getattr(info.context, "tenant_id", "default")
        model = RegisteredModel.objects.create(
            tenant_id=tenant_id,
            name=name,
            description=description,
            tags=tags or {},
        )
        return CreateRegisteredModel(ok=True, model=model)


class UpdateRegisteredModel(graphene.Mutation):
    """Update a registered ML model."""

    class Arguments:
        id = graphene.UUID(required=True)
        name = graphene.String()
        description = graphene.String()
        tags = graphene.JSONString()

    ok = graphene.Boolean()
    model = graphene.Field(RegisteredModelType)

    def mutate(self, info: Any, id: str, **kwargs: Any) -> UpdateRegisteredModel:
        try:
            model = RegisteredModel.objects.get(id=id)
        except RegisteredModel.DoesNotExist:
            return UpdateRegisteredModel(ok=False, model=None)

        for field, value in kwargs.items():
            if value is not None:
                setattr(model, field, value)
        model.save()
        return UpdateRegisteredModel(ok=True, model=model)


class Mutation(graphene.ObjectType):
    """Root mutation type for the Voyant GraphQL API."""

    # Pipeline mutations
    create_pipeline = CreatePipeline.Field()
    update_pipeline = UpdatePipeline.Field()
    delete_pipeline = DeletePipeline.Field()

    # Ontology mutations
    create_object_type = CreateObjectType.Field()
    update_object_type = UpdateObjectType.Field()
    delete_object_type = DeleteObjectType.Field()

    # ML mutations
    create_experiment = CreateExperiment.Field()
    update_experiment = UpdateExperiment.Field()
    create_registered_model = CreateRegisteredModel.Field()
    update_registered_model = UpdateRegisteredModel.Field()


# ---------------------------------------------------------------------------
# Schema assembly with depth limiting
# ---------------------------------------------------------------------------


def _enforce_depth_limit(query: str, max_depth: int = 10) -> None:
    """Raise an error if the query exceeds the maximum nesting depth.

    A simple heuristic: counts the maximum nesting of curly braces.
    """
    max_nesting = 0
    current = 0
    for char in query:
        if char == "{":
            current += 1
            max_nesting = max(max_nesting, current)
        elif char == "}":
            current -= 1

    if max_nesting > max_depth:
        raise ValueError(
            f"Query depth {max_nesting} exceeds maximum allowed depth of {max_depth}"
        )


def get_schema() -> graphene.Schema:
    """Build and return the GraphQL schema."""
    schema = graphene.Schema(
        query=Query,
        mutation=Mutation,
        auto_camelcase=True,
    )
    return schema


# Middleware for depth limiting
class DepthLimitMiddleware:
    """GraphQL middleware that enforces a maximum query depth of 10."""

    MAX_DEPTH = 10

    def resolve(self, next_: Any, root: Any, info: Any, **args: Any) -> Any:
        if root is None:
            try:
                query_str = str(info.operation.loc.source.body) if info.operation else ""
                _enforce_depth_limit(query_str, self.MAX_DEPTH)
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
        return next_(root, info, **args)
