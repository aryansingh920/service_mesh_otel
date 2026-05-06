istioctl install --set profile=demo -y

kubectl get pods -n istio-system


kubectl create namespace mesh-apps
kubectl label namespace mesh-apps istio-injection=enabled

kubectl apply -f service/services.yaml


curl -L https://istio.io/downloadIstio | sh -
cd istio-*
export PATH=$PWD/bin:$PATH

echo 'export PATH="$PATH:/Users/aryansingh/Desktop/service_mesh_otel/istio-1.29.2/bin"' >> ~/.zshrc
source ~/.zshrc

istioctl dashboard kiali
