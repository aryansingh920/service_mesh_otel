istioctl install --set profile=demo -y

kubectl get pods -n istio-system


kubectl create namespace mesh-apps
kubectl label namespace mesh-apps istio-injection=enabled

kubectl apply -f service/services.yaml
