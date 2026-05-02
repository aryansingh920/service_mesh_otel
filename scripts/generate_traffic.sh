# # Get the frontend pod name
# export FRONTEND_POD=$(kubectl get pod -l app=frontend -n mesh-apps -o jsonpath='{.items[0].metadata.name}')

# # Start a loop that curls the backend once per second
# kubectl exec -it $FRONTEND_POD -n mesh-apps -- /bin/sh -c "while true; do curl -s http://backend.mesh-apps.svc.cluster.local; echo ' -> Request sent at \$(date)'; sleep 1; done"



kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.21/samples/sleep/sleep.yaml -n mesh-apps
kubectl exec -it $(kubectl get pod -l app=sleep -n mesh-apps -o jsonpath='{.items[0].metadata.name}') -n mesh-apps -- sh -c "while true; do curl -s http://frontend.mesh-apps.svc.cluster.local; sleep 1; done"


# frontend to backend flow
kubectl exec -it $(kubectl get pod -l app=sleep -n mesh-apps -o jsonpath='{.items[0].metadata.name}') -n mesh-apps -- sh -c "while true; do curl -s http://frontend.mesh-apps.svc.cluster.local && curl -s http://backend.mesh-apps.svc.cluster.local; sleep 1; done"


# Backend to DB flow
kubectl exec -it $(kubectl get pod -l app=sleep -n mesh-apps -o jsonpath='{.items[0].metadata.name}') -n mesh-apps -- sh -c "while true; do curl -s http://db-simulator.mesh-apps.svc.cluster.local; sleep 2; done"


# chain call
kubectl exec -it $(kubectl get pod -l app=sleep -n mesh-apps -o jsonpath='{.items[0].metadata.name}') -n mesh-apps -- sh -c "
while true; do 
  echo '--- New Request Chain ---';
  # 1. Sleep calls Frontend
  curl -s http://frontend.mesh-apps.svc.cluster.local;
  # 2. We simulate the Frontend calling the Backend
  kubectl exec -n mesh-apps \$(kubectl get pod -l app=frontend -n mesh-apps -o jsonpath='{.items[0].metadata.name}') -c app -- curl -s http://backend.mesh-apps.svc.cluster.local;
  # 3. We simulate the Backend calling the DB
  kubectl exec -n mesh-apps \$(kubectl get pod -l app=backend -n mesh-apps -o jsonpath='{.items[0].metadata.name}') -c app -- curl -s http://db-simulator.mesh-apps.svc.cluster.local;
  sleep 2;
done"
