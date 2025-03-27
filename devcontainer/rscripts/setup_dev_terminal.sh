log_current_context() {
    #echo "Current context: $(kubectl config current-context)"
    #echo "Current namespace: $(kubectl config view --minify --output 'jsonpath={..namespace}')"
    echo "$(kubectl config current-context) / $(kubectl config view --minify --output 'jsonpath={..namespace}')"
}

k_get_contexts() {
    #kubectl config get-contexts -o=name
    kubectl config get-contexts --no-headers | awk '{print ($1 == "*" ? "[ACTIVE] " $2 : $2)}'
}

k_use_context() {
    kubectl config use-context $1
}

get_worksync_status() {
	kubectl get worksync $1 -n flux-system -o custom-columns="READY:.status.conditions[?(@.type=='Ready')].status,REASON:.status.conditions[?(@.type=='Ready')].reason,LAST_APPLIED:.status.lastAppliedRevision,LAST_ATTEMPTED:.status.lastAttemptedRevision,INDEX_STATUS:.status.indexStatus.status,INDEX_FINISHED:.status.indexStatus.lastIndexFinishedAt,LastHandledReconcileAt:.status.lastHandledReconcileAt"
}

echo "Welcome to the development environment"
echo "Any time use help_banner to see useful commands"

help_banner() {
    # Banner
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
    echo "kubectl scale deployment <serviceName> --replicas=1"
    echo "e.g.  kubectl scale deployment papi --replicas=1"
    echo "notes: Do this before you okteto into pod which guarantees that yours is only instance running"
    echo "---------------------------------------------------------------------------------"
    echo "Okteto into service"
    echo "okteto up <serviceName>"
    echo "e.g.   okteto up papi"
    echo "notes: You need to run this command from service code folder which has service specific okteto.yml file"
    echo "---------------------------------------------------------------------------------"
    echo "Get postgres password"
    echo "kubectl -n backend-services get secrets core-pguser-core -o 'go-template={{range \$k,\$v := .data}}{{printf \"%s: \" \$k}}{{if not \$v}}{{\$v}}{{else}}{{\$v | base64decode}}{{end}}{{\"\\\\n\"}}{{end}}'"
    echo "notes: Command assumes that your current context is platform cluster"
    echo "---------------------------------------------------------------------------------"
    echo "Forward postgres port to local machine"
    echo "kubectl -n backend-services port-forward svc/core-pgadmin 5050 --address=0.0.0.0"
    echo "notes: After this open http://localhost:5000" to open pgbouncer, username: core@pgo and password: recived in "kubectl -n backend-services get secrets core-pguser-core ..." command
    echo "---------------------------------------------------------------------------------"
}

help_banner

cd $SRC_BASE_PATH
