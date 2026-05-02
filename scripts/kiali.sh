# Apply the Kiali and Prometheus addons (Kiali needs Prometheus to see metrics)
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.21/samples/addons/prometheus.yaml
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.21/samples/addons/kiali.yaml


istioctl dashboard kiali
