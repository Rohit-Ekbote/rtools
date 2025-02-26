log_current_context() {
    echo "Current context: $(kubectl config current-context)"
    echo "Current namespace: $(kubectl config view --minify --output 'jsonpath={..namespace}')"
}


cd $SRC_BASE_PATH

# Banner
echo "Welcome to the development environment"
#echo "Current directory: $(pwd)"
#echo "Current namespace: $(kubectl config view --minify --output 'jsonpath={..namespace}')"
#echo "Current context: $(kubectl config current-context)"
echo "Following are some useful commands"
echo "---------------------------------------------------------------------------------"
echo "Login to google cloud"
echo "gcloud auth login"
echo "---------------------------------------------------------------------------------"
echo "Set env/project"
echo "gcloud config set project <projectID>"
echo "e.g.  gcloud config set project runwhen-nonprod-wolf"
echo "---------------------------------------------------------------------------------"
echo "Check gcloud auth by listing clusters"
echo "gcloud container clusters"
echo "---------------------------------------------------------------------------------"
echo "Get cluster credentials"
echo "gcloud container clusters get-credentials --project <projectID> --region <region> <clusterName>"
echo "e.g.  gcloud container clusters get-credentials --project runwhen-nonprod-wolf --region us-central1 platform-cluster"
echo "notes: This also sets context to this cluster"
echo "---------------------------------------------------------------------------------"
echo "List contexts"
echo "kubectl config get-contexts"
echo "---------------------------------------------------------------------------------"
echo "Suspend namespace from flux"
echo "flux suspend kustomization <namespaceID>"
echo "e.g.  flux suspend kustomization runwhen-backend-services"
echo "---------------------------------------------------------------------------------"
echo "Set replicaset count to 1"
echo "flux suspend kustomization <namespaceID>"
echo "e.g.  flux suspend kustomization runwhen-backend-services"
echo "notes: Do this before you okteto into pod which guarantees that yours is only instance running"
echo "---------------------------------------------------------------------------------"
echo "Okteto into service"
echo "okteto up <serviceName>"
echo "e.g.   okteto up papi"
echo "notes: You need to run this command from service code folder which has service specific okteto.yml file"
echo "---------------------------------------------------------------------------------"
echo "Get postgres password"
echo "kubectl -n backend-services get secrets core-pguser-core  -o go-template='{{range $k,$v := .data}}{{printf "%s: " $k}}{{if not $v}}{{$v}}{{else}}{{$v | base64decode}}{{end}}{{"\n"}}{{end}}'"
echo "notes: Command assumes that your current context is platform cluster"
echo "---------------------------------------------------------------------------------"
echo "Forward postgres port to local machine"
echo "kubectl -n backend-services port-forward svc/core-pgadmin 5050 --address=0.0.0.0"
echo "notes: After this open http://localhost:5000" to open pgbouncer, username: pg@core and password: <recived in `kubectl -n backend-services get secrets core-pguser-core ...` command>
echo "---------------------------------------------------------------------------------"

# login to gcloud
# gcloud_login

# set environment
# set_env runwhen-nonprod-wolf
# gcloud config set project runwhen-nonprod-wolf

# get cluster credentials
# get_cluster_credentials platform-cluster
# gcloud container clusters get-credentials --project runwhen-nonprod-wolf --region us-central1 platform-cluster

# set context to specific namespace
# kubectl config set-context --current --namespace=backend-services

# suspend namespace from flux
# flux suspend kustomization runwhen-backend-services

# set replicaset count to 1
# kubectl scale deployment papi --replicas=1

# move into service directory (which has okteto.yml)
# okteto up papi

# command to get postgres password
# kubectl -n backend-services get secrets core-pguser-core  -o go-template='{{range $k,$v := .data}}{{printf "%s: " $k}}{{if not $v}}{{$v}}{{else}}{{$v | base64decode}}{{end}}{{"\n"}}{{end}}'

# command to forward postgres port to local machine
# kubectl -n backend-services port-forward svc/core-pgadmin 5050 --address=0.0.0.0