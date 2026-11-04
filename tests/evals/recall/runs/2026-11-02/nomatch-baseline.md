The usual setup is to expose a metric from Go, have Prometheus scrape it, and use **prometheus-adapter** to publish it through the Kubernetes custom metrics API so an `autoscaling/v2` HPA can read it. [KEDA](#keda-alternative) is the main alternative. I've used prometheus-adapter below and assumed you run the Prometheus Operator, because of the `ServiceMonitor`. This is from memory and hasn't been tested on a cluster, so check the chart values against your version.

### 1. Expose a metric from the Go service

```go
package main

import (
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var requests = promauto.NewCounterVec(
	prometheus.CounterOpts{Name: "http_requests_total", Help: "HTTP requests handled."},
	[]string{"code"},
)

func handler(w http.ResponseWriter, r *http.Request) {
	requests.WithLabelValues("200").Inc()
	w.Write([]byte("ok"))
}

func main() {
	http.HandleFunc("/", handler)
	http.Handle("/metrics", promhttp.Handler())
	http.ListenAndServe(":8080", nil)
}
```

### 2. Scrape it

The `ServiceMonitor` refers to the Service port by name, so the port must have one.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-go-app
  labels:
    app: my-go-app
spec:
  selector:
    app: my-go-app
  ports:
    - name: http
      port: 8080
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: my-go-app
  labels:
    release: prometheus   # must match your Prometheus serviceMonitorSelector
spec:
  selector:
    matchLabels:
      app: my-go-app
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

### 3. Install prometheus-adapter

Create `adapter-values.yaml`, which turns the counter into a per-second rate metric:

```yaml
prometheus:
  url: http://prometheus-operated.monitoring.svc
  port: 9090

rules:
  custom:
    - seriesQuery: 'http_requests_total{namespace!="",pod!=""}'
      resources:
        overrides:
          namespace: {resource: "namespace"}
          pod: {resource: "pod"}
      name:
        matches: "^(.*)_total$"
        as: "${1}_per_second"
      metricsQuery: 'sum(rate(<<.Series>>{<<.LabelMatchers>>}[2m])) by (<<.GroupBy>>)'
```

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus-adapter prometheus-community/prometheus-adapter \
  -n monitoring -f adapter-values.yaml
```

### 4. Check that the metric is available

Do this before creating the HPA, because most failures show up here:

```bash
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta2/namespaces/default/pods/*/http_requests_per_second"
```

If you get a `NotFound` error, check the adapter logs and confirm the series in Prometheus has `namespace` and `pod` labels.

### 5. Create the HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-go-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-go-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"   # target per pod
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 300
```

Confirm it's working with `kubectl describe hpa my-go-app`. The `TARGETS` column in `kubectl get hpa` may show values like `1500m`, which means 1.5 requests per second.

### Common problems

- **`<unknown>` targets:** the HPA can't read the metric, so run the check in step 4 and look at the `kubectl describe hpa` events.
- **Metric missing after creating the `ServiceMonitor`:** the `release` label doesn't match the Prometheus selector, or the port name doesn't match.
- **Scaling lags or flaps:** the `rate()` window should be at least 4× the scrape interval. A longer window is smoother but reacts more slowly.
- **Scaling from zero:** a standard HPA stops at `minReplicas: 1`, and a pod-based metric has no data with no pods running. Use KEDA if you need to scale to zero.
- **Too many Prometheus series:** don't use user IDs or raw URLs as metric labels.
- **Metric choice:** request rate suits stateless services, while queue depth or in-flight requests suit workers better. Add a CPU target to the same HPA if you want a safety net. The HPA uses whichever metric asks for the most replicas.

### KEDA alternative

KEDA needs no adapter rules and supports scaling to zero. It queries Prometheus directly and creates the HPA for you, so don't also attach your own HPA to the same Deployment.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: my-go-app
spec:
  scaleTargetRef:
    name: my-go-app
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus-operated.monitoring.svc:9090
        query: sum(rate(http_requests_total{namespace="default",service="my-go-app"}[2m]))
        threshold: "100"
```

For a new setup, I'd pick KEDA if you want scale-to-zero or event-based triggers. If you only need one or two metrics and want plain HPA objects, stick with prometheus-adapter.
