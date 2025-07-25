# Configuring a "Stack"

The Llama Stack runtime configuration is specified as a YAML file. Here is a simplified version of an example configuration file for the Ollama distribution:

```{note}
The default `run.yaml` files generated by templates are starting points for your configuration. For guidance on customizing these files for your specific needs, see [Customizing Your run.yaml Configuration](customizing_run_yaml.md).
```

```{dropdown} 👋 Click here for a Sample Configuration File

```yaml
version: 2
conda_env: ollama
apis:
- agents
- inference
- vector_io
- safety
- telemetry
providers:
  inference:
  - provider_id: ollama
    provider_type: remote::ollama
    config:
      url: ${env.OLLAMA_URL:=http://localhost:11434}
  vector_io:
  - provider_id: faiss
    provider_type: inline::faiss
    config:
      kvstore:
        type: sqlite
        namespace: null
        db_path: ${env.SQLITE_STORE_DIR:=~/.llama/distributions/ollama}/faiss_store.db
  safety:
  - provider_id: llama-guard
    provider_type: inline::llama-guard
    config: {}
  agents:
  - provider_id: meta-reference
    provider_type: inline::meta-reference
    config:
      persistence_store:
        type: sqlite
        namespace: null
        db_path: ${env.SQLITE_STORE_DIR:=~/.llama/distributions/ollama}/agents_store.db
  telemetry:
  - provider_id: meta-reference
    provider_type: inline::meta-reference
    config: {}
metadata_store:
  namespace: null
  type: sqlite
  db_path: ${env.SQLITE_STORE_DIR:=~/.llama/distributions/ollama}/registry.db
models:
- metadata: {}
  model_id: ${env.INFERENCE_MODEL}
  provider_id: ollama
  provider_model_id: null
shields: []
server:
  port: 8321
  auth:
    provider_config:
      type: "oauth2_token"
      jwks:
        uri: "https://my-token-issuing-svc.com/jwks"
```

Let's break this down into the different sections. The first section specifies the set of APIs that the stack server will serve:
```yaml
apis:
- agents
- inference
- vector_io
- safety
- telemetry
```

## Providers
Next up is the most critical part: the set of providers that the stack will use to serve the above APIs. Consider the `inference` API:
```yaml
providers:
  inference:
    # provider_id is a string you can choose freely
  - provider_id: ollama
    # provider_type is a string that specifies the type of provider.
    # in this case, the provider for inference is ollama and it runs remotely (outside of the distribution)
    provider_type: remote::ollama
    # config is a dictionary that contains the configuration for the provider.
    # in this case, the configuration is the url of the ollama server
    config:
      url: ${env.OLLAMA_URL:=http://localhost:11434}
```
A few things to note:
- A _provider instance_ is identified with an (id, type, config) triplet.
- The id is a string you can choose freely.
- You can instantiate any number of provider instances of the same type.
- The configuration dictionary is provider-specific.
- Notice that configuration can reference environment variables (with default values), which are expanded at runtime. When you run a stack server (via docker or via `llama stack run`), you can specify `--env OLLAMA_URL=http://my-server:11434` to override the default value.

### Environment Variable Substitution

Llama Stack supports environment variable substitution in configuration values using the
`${env.VARIABLE_NAME}` syntax. This allows you to externalize configuration values and provide
different settings for different environments. The syntax is inspired by [bash parameter expansion](https://www.gnu.org/software/bash/manual/html_node/Shell-Parameter-Expansion.html)
and follows similar patterns.

#### Basic Syntax

The basic syntax for environment variable substitution is:

```yaml
config:
  api_key: ${env.API_KEY}
  url: ${env.SERVICE_URL}
```

If the environment variable is not set, the server will raise an error during startup.

#### Default Values

You can provide default values using the `:=` operator:

```yaml
config:
  url: ${env.OLLAMA_URL:=http://localhost:11434}
  port: ${env.PORT:=8321}
  timeout: ${env.TIMEOUT:=60}
```

If the environment variable is not set, the default value `http://localhost:11434` will be used.
Empty defaults are allowed so `url: ${env.OLLAMA_URL:=}` will be set to `None` if the environment variable is not set.

#### Conditional Values

You can use the `:+` operator to provide a value only when the environment variable is set:

```yaml
config:
  # Only include this field if ENVIRONMENT is set
  environment: ${env.ENVIRONMENT:+production}
```

If the environment variable is set, the value after `:+` will be used. If it's not set, the field
will be omitted with a `None` value.

Do not use conditional values (`${env.OLLAMA_URL:+}`) for empty defaults (`${env.OLLAMA_URL:=}`).
This will be set to `None` if the environment variable is not set.
Conditional must only be used when the environment variable is set.

#### Examples

Here are some common patterns:

```yaml
# Required environment variable (will error if not set)
api_key: ${env.OPENAI_API_KEY}

# Optional with default
base_url: ${env.API_BASE_URL:=https://api.openai.com/v1}

# Conditional field
debug_mode: ${env.DEBUG:+true}

# Optional field that becomes None if not set
optional_token: ${env.OPTIONAL_TOKEN:+}
```

#### Runtime Override

You can override environment variables at runtime when starting the server:

```bash
# Override specific environment variables
llama stack run --config run.yaml --env API_KEY=sk-123 --env BASE_URL=https://custom-api.com

# Or set them in your shell
export API_KEY=sk-123
export BASE_URL=https://custom-api.com
llama stack run --config run.yaml
```

#### Type Safety

The environment variable substitution system is type-safe:

- String values remain strings
- Empty defaults (`${env.VAR:+}`) are converted to `None` for fields that accept `str | None`
- Numeric defaults are properly typed (e.g., `${env.PORT:=8321}` becomes an integer)
- Boolean defaults work correctly (e.g., `${env.DEBUG:=false}` becomes a boolean)

## Resources

Let's look at the `models` section:

```yaml
models:
- metadata: {}
  model_id: ${env.INFERENCE_MODEL}
  provider_id: ollama
  provider_model_id: null
  model_type: llm
```
A Model is an instance of a "Resource" (see [Concepts](../concepts/index)) and is associated with a specific inference provider (in this case, the provider with identifier `ollama`). This is an instance of a "pre-registered" model. While we always encourage the clients to register models before using them, some Stack servers may come up a list of "already known and available" models.

What's with the `provider_model_id` field? This is an identifier for the model inside the provider's model catalog. Contrast it with `model_id` which is the identifier for the same model for Llama Stack's purposes. For example, you may want to name "llama3.2:vision-11b" as "image_captioning_model" when you use it in your Stack interactions. When omitted, the server will set `provider_model_id` to be the same as `model_id`.

If you need to conditionally register a model in the configuration, such as only when specific environment variable(s) are set, this can be accomplished by utilizing a special `__disabled__` string as the default value of an environment variable substitution, as shown below:

```yaml
models:
- metadata: {}
  model_id: ${env.INFERENCE_MODEL:__disabled__}
  provider_id: ollama
  provider_model_id: ${env.INFERENCE_MODEL:__disabled__}
```

The snippet above will only register this model if the environment variable `INFERENCE_MODEL` is set and non-empty. If the environment variable is not set, the model will not get registered at all.

## Server Configuration

The `server` section configures the HTTP server that serves the Llama Stack APIs:

```yaml
server:
  port: 8321  # Port to listen on (default: 8321)
  tls_certfile: "/path/to/cert.pem"  # Optional: Path to TLS certificate for HTTPS
  tls_keyfile: "/path/to/key.pem"    # Optional: Path to TLS key for HTTPS
```

### Authentication Configuration

> **Breaking Change (v0.2.14)**: The authentication configuration structure has changed. The previous format with `provider_type` and `config` fields has been replaced with a unified `provider_config` field that includes the `type` field. Update your configuration files accordingly.

The `auth` section configures authentication for the server. When configured, all API requests must include a valid Bearer token in the Authorization header:

```
Authorization: Bearer <token>
```

The server supports multiple authentication providers:

#### OAuth 2.0/OpenID Connect Provider with Kubernetes

The server can be configured to use service account tokens for authorization, validating these against the Kubernetes API server, e.g.:
```yaml
server:
  auth:
    provider_config:
      type: "oauth2_token"
      jwks:
        uri: "https://kubernetes.default.svc:8443/openid/v1/jwks"
        token: "${env.TOKEN:+}"
        key_recheck_period: 3600
      tls_cafile: "/path/to/ca.crt"
      issuer: "https://kubernetes.default.svc"
      audience: "https://kubernetes.default.svc"
```

To find your cluster's jwks uri (from which the public key(s) to verify the token signature are obtained), run:
```
kubectl get --raw /.well-known/openid-configuration| jq -r .jwks_uri
```

For the tls_cafile, you can use the CA certificate of the OIDC provider:
```bash
kubectl config view --minify -o jsonpath='{.clusters[0].cluster.certificate-authority}'
```

For the issuer, you can use the OIDC provider's URL:
```bash
kubectl get --raw /.well-known/openid-configuration| jq .issuer
```

The audience can be obtained from a token, e.g. run:
```bash
kubectl create token default --duration=1h | cut -d. -f2 | base64 -d | jq .aud
```

The jwks token is used to authorize access to the jwks endpoint. You can obtain a token by running:

```bash
kubectl create namespace llama-stack
kubectl create serviceaccount llama-stack-auth -n llama-stack
kubectl create token llama-stack-auth -n llama-stack > llama-stack-auth-token
export TOKEN=$(cat llama-stack-auth-token)
```

Alternatively, you can configure the jwks endpoint to allow anonymous access. To do this, make sure
the `kube-apiserver` runs with `--anonymous-auth=true` to allow unauthenticated requests
and that the correct RoleBinding is created to allow the service account to access the necessary
resources. If that is not the case, you can create a RoleBinding for the service account to access
the necessary resources:

```yaml
# allow-anonymous-openid.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: allow-anonymous-openid
rules:
- nonResourceURLs: ["/openid/v1/jwks"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: allow-anonymous-openid
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: allow-anonymous-openid
subjects:
- kind: User
  name: system:anonymous
  apiGroup: rbac.authorization.k8s.io
```

And then apply the configuration:
```bash
kubectl apply -f allow-anonymous-openid.yaml
```

The provider extracts user information from the JWT token:
- Username from the `sub` claim becomes a role
- Kubernetes groups become teams

You can easily validate a request by running:

```bash
curl -s -L -H "Authorization: Bearer $(cat llama-stack-auth-token)" http://127.0.0.1:8321/v1/providers
```

#### GitHub Token Provider
Validates GitHub personal access tokens or OAuth tokens directly:
```yaml
server:
  auth:
    provider_config:
      type: "github_token"
      github_api_base_url: "https://api.github.com"  # Or GitHub Enterprise URL
```

The provider fetches user information from GitHub and maps it to access attributes based on the `claims_mapping` configuration.

#### Custom Provider
Validates tokens against a custom authentication endpoint:
```yaml
server:
  auth:
    provider_config:
      type: "custom"
      endpoint: "https://auth.example.com/validate"  # URL of the auth endpoint
```

The custom endpoint receives a POST request with:
```json
{
  "api_key": "<token>",
  "request": {
    "path": "/api/v1/endpoint",
    "headers": {
      "content-type": "application/json",
      "user-agent": "curl/7.64.1"
    },
    "params": {
      "key": ["value"]
    }
  }
}
```

And must respond with:
```json
{
  "access_attributes": {
    "roles": ["admin", "user"],
    "teams": ["ml-team", "nlp-team"],
    "projects": ["llama-3", "project-x"],
    "namespaces": ["research"]
  },
  "message": "Authentication successful"
}
```

If no access attributes are returned, the token is used as a namespace.

### Access control

When authentication is enabled, access to resources is controlled
through the `access_policy` attribute of the auth config section under
server. The value for this is a list of access rules.

Each access rule defines a list of actions either to permit or to
forbid. It may specify a principal or a resource that must match for
the rule to take effect.

Valid actions are create, read, update, and delete. The resource to
match should be specified in the form of a type qualified identifier,
e.g.  model::my-model or vector_db::some-db, or a wildcard for all
resources of a type, e.g. model::*. If the principal or resource are
not specified, they will match all requests.

The valid resource types are model, shield, vector_db, dataset,
scoring_function, benchmark, tool, tool_group and session.

A rule may also specify a condition, either a 'when' or an 'unless',
with additional constraints as to where the rule applies. The
constraints supported at present are:

 - 'user with <attr-value> in <attr-name>'
 - 'user with <attr-value> not in <attr-name>'
 - 'user is owner'
 - 'user is not owner'
 - 'user in owners <attr-name>'
 - 'user not in owners <attr-name>'

The attributes defined for a user will depend on how the auth
configuration is defined.

When checking whether a particular action is allowed by the current
user for a resource, all the defined rules are tested in order to find
a match. If a match is found, the request is permitted or forbidden
depending on the type of rule. If no match is found, the request is
denied.

If no explicit rules are specified, a default policy is defined with
which all users can access all resources defined in config but
resources created dynamically can only be accessed by the user that
created them.

Examples:

The following restricts access to particular github users:

```yaml
server:
  auth:
    provider_config:
      type: "github_token"
      github_api_base_url: "https://api.github.com"
  access_policy:
  - permit:
      principal: user-1
      actions: [create, read, delete]
    description: user-1 has full access to all resources
  - permit:
      principal: user-2
      actions: [read]
      resource: model::model-1
    description: user-2 has read access to model-1 only
```

Similarly, the following restricts access to particular kubernetes
service accounts:

```yaml
server:
  auth:
    provider_config:
      type: "oauth2_token"
      audience: https://kubernetes.default.svc.cluster.local
      issuer: https://kubernetes.default.svc.cluster.local
      tls_cafile: /home/gsim/.minikube/ca.crt
      jwks:
        uri: https://kubernetes.default.svc.cluster.local:8443/openid/v1/jwks
        token: ${env.TOKEN}
    access_policy:
    - permit:
        principal: system:serviceaccount:my-namespace:my-serviceaccount
        actions: [create, read, delete]
      description: specific serviceaccount has full access to all resources
    - permit:
        principal: system:serviceaccount:default:default
        actions: [read]
        resource: model::model-1
      description: default account has read access to model-1 only
```

The following policy, which assumes that users are defined with roles
and teams by whichever authentication system is in use, allows any
user with a valid token to use models, create resources other than
models, read and delete resources they created and read resources
created by users sharing a team with them:

```
    access_policy:
    - permit:
        actions: [read]
        resource: model::*
      description: all users have read access to models
    - forbid:
        actions: [create, delete]
        resource: model::*
      unless: user with admin in roles
      description: only user with admin role can create or delete models
    - permit:
        actions: [create, read, delete]
      when: user is owner
      description: users can create resources other than models and read and delete those they own
    - permit:
        actions: [read]
      when: user in owner teams
      description: any user has read access to any resource created by a user with the same team
```

#### API Endpoint Authorization with Scopes

In addition to resource-based access control, Llama Stack supports endpoint-level authorization using OAuth 2.0 style scopes. When authentication is enabled, specific API endpoints require users to have particular scopes in their authentication token.

**Scope-Gated APIs:**
The following APIs are currently gated by scopes:

- **Telemetry API** (scope: `telemetry.read`):
  - `POST /telemetry/traces` - Query traces
  - `GET /telemetry/traces/{trace_id}` - Get trace by ID
  - `GET /telemetry/traces/{trace_id}/spans/{span_id}` - Get span by ID
  - `POST /telemetry/spans/{span_id}/tree` - Get span tree
  - `POST /telemetry/spans` - Query spans
  - `POST /telemetry/metrics/{metric_name}` - Query metrics

**Authentication Configuration:**

For **JWT/OAuth2 providers**, scopes should be included in the JWT's claims:
```json
{
  "sub": "user123",
  "scope": "telemetry.read",
  "aud": "llama-stack"
}
```

For **custom authentication providers**, the endpoint must return user attributes including the `scopes` array:
```json
{
  "principal": "user123",
  "attributes": {
    "scopes": ["telemetry.read"]
  }
}
```

**Behavior:**
- Users without the required scope receive a 403 Forbidden response
- When authentication is disabled, scope checks are bypassed
- Endpoints without `required_scope` work normally for all authenticated users

### Quota Configuration

The `quota` section allows you to enable server-side request throttling for both
authenticated and anonymous clients. This is useful for preventing abuse, enforcing
fairness across tenants, and controlling infrastructure costs without requiring
client-side rate limiting or external proxies.

Quotas are disabled by default. When enabled, each client is tracked using either:

* Their authenticated `client_id` (derived from the Bearer token), or
* Their IP address (fallback for anonymous requests)

Quota state is stored in a SQLite-backed key-value store, and rate limits are applied
within a configurable time window (currently only `day` is supported).

#### Example

```yaml
server:
  quota:
    kvstore:
      type: sqlite
      db_path: ./quotas.db
    anonymous_max_requests: 100
    authenticated_max_requests: 1000
    period: day
```

#### Configuration Options

| Field                        | Description                                                                |
| ---------------------------- | -------------------------------------------------------------------------- |
| `kvstore`                    | Required. Backend storage config for tracking request counts.              |
| `kvstore.type`               | Must be `"sqlite"` for now. Other backends may be supported in the future. |
| `kvstore.db_path`            | File path to the SQLite database.                                          |
| `anonymous_max_requests`     | Max requests per period for unauthenticated clients.                       |
| `authenticated_max_requests` | Max requests per period for authenticated clients.                         |
| `period`                     | Time window for quota enforcement. Only `"day"` is supported.              |

> Note: if `authenticated_max_requests` is set but no authentication provider is
configured, the server will fall back to applying `anonymous_max_requests` to all
clients.

#### Example with Authentication Enabled

```yaml
server:
  port: 8321
  auth:
    provider_config:
      type: custom
      endpoint: https://auth.example.com/validate
  quota:
    kvstore:
      type: sqlite
      db_path: ./quotas.db
    anonymous_max_requests: 100
    authenticated_max_requests: 1000
    period: day
```

If a client exceeds their limit, the server responds with:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json

{
  "error": {
    "message": "Quota exceeded"
  }
}
```

## Extending to handle Safety

Configuring Safety can be a little involved so it is instructive to go through an example.

The Safety API works with the associated Resource called a `Shield`. Providers can support various kinds of Shields. Good examples include the [Llama Guard](https://ai.meta.com/research/publications/llama-guard-llm-based-input-output-safeguard-for-human-ai-conversations/) system-safety models, or [Bedrock Guardrails](https://aws.amazon.com/bedrock/guardrails/).

To configure a Bedrock Shield, you would need to add:
- A Safety API provider instance with type `remote::bedrock`
- A Shield resource served by this provider.

```yaml
...
providers:
  safety:
  - provider_id: bedrock
    provider_type: remote::bedrock
    config:
      aws_access_key_id: ${env.AWS_ACCESS_KEY_ID}
      aws_secret_access_key: ${env.AWS_SECRET_ACCESS_KEY}
...
shields:
- provider_id: bedrock
  params:
    guardrailVersion: ${env.GUARDRAIL_VERSION}
  provider_shield_id: ${env.GUARDRAIL_ID}
...
```

The situation is more involved if the Shield needs _Inference_ of an associated model. This is the case with Llama Guard. In that case, you would need to add:
- A Safety API provider instance with type `inline::llama-guard`
- An Inference API provider instance for serving the model.
- A Model resource associated with this provider.
- A Shield resource served by the Safety provider.

The yaml configuration for this setup, assuming you were using vLLM as your inference server, would look like:
```yaml
...
providers:
  safety:
  - provider_id: llama-guard
    provider_type: inline::llama-guard
    config: {}
  inference:
  # this vLLM server serves the "normal" inference model (e.g., llama3.2:3b)
  - provider_id: vllm-0
    provider_type: remote::vllm
    config:
      url: ${env.VLLM_URL:=http://localhost:8000}
  # this vLLM server serves the llama-guard model (e.g., llama-guard:3b)
  - provider_id: vllm-1
    provider_type: remote::vllm
    config:
      url: ${env.SAFETY_VLLM_URL:=http://localhost:8001}
...
models:
- metadata: {}
  model_id: ${env.INFERENCE_MODEL}
  provider_id: vllm-0
  provider_model_id: null
- metadata: {}
  model_id: ${env.SAFETY_MODEL}
  provider_id: vllm-1
  provider_model_id: null
shields:
- provider_id: llama-guard
  shield_id: ${env.SAFETY_MODEL}   # Llama Guard shields are identified by the corresponding LlamaGuard model
  provider_shield_id: null
...
```
