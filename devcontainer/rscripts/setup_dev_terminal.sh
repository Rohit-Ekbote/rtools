gcloud_login() {
    # Check if already authenticated
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1; then
        echo "Already logged into gcloud as $(gcloud config get-value account)"
        return 0
    fi

    # Attempt login
    if gcloud auth login; then
        echo "Successfully logged into gcloud as $(gcloud config get-value account)"
    else
        echo "Failed to log into gcloud"
        return 1
    fi
}

log_current_context() {
    echo "Current context: $(kubectl config current-context)"
    echo "Current namespace: $(kubectl config view --minify --output 'jsonpath={..namespace}')"
}

set_env() {
    if [ -z "$1" ]; then
        echo "Please provide an environment name"
        return 1
    fi
    export RW_ENV="$1"

    if [ -z "$2" ]; then
        echo "Using default region: us-central1"
    fi
    export RW_REGION="${2:-us-central1}"

    # gcloud container clusters get-credentials platform-cluster --project runwhen-nonprod-kyle --region us-central1
    gcloud config set project $RW_ENV
    #gcloud config set compute/region $RW_REGION
    #gcloud container clusters get-credentials platform-cluster --project $RW_ENV
    # list all clusters, so we can see if we have set correct project and region
    gcloud container clusters list
}

get_cluster_credentials() {
    
    if [ -z "$1" ]; then
        echo "Please provide a cluster context name"
        return 1
    fi
    
    gcloud container clusters get-credentials $1 --project $RW_ENV --region $RW_REGION
    # Verify the context was set
    log_current_context
}


set_namespace() {
    if [ -z "$1" ]; then
        echo "Please provide a namespace"
        return 1
    fi
    kubectl config set-context --current --namespace="$1"
    # Verify the namespace was set
    log_current_context
}

suspend_namespace_flux() {
    if [ -z "$1" ]; then
        echo "Please provide a namespace to suspend from Flux"
        return 1
    fi
    
    # Suspend all Kustomizations in the namespace
    echo "Suspending Kustomizations in namespace $1..."
    flux suspend kustomization --namespace "$1" --all
    
    # Suspend all HelmReleases in the namespace
    echo "Suspending HelmReleases in namespace $1..."
    flux suspend helmrelease --namespace "$1" --all
    
    echo "Flux resources suspended in namespace $1"
}


cd $SRC_BASE_PATH

# Banner
echo "Welcome to the development environment"
echo "Current directory: $(pwd)"
echo "Current namespace: $(kubectl config view --minify --output 'jsonpath={..namespace}')"
echo "Current context: $(kubectl config current-context)"

# login to gcloud
# gcloud_login

# set environment
# set_env runwhen-nonprod-wolf

# get cluster credentials
# get_cluster_credentials platform-cluster
# gcloud container clusters get-credentials --project runwhen-nonprod-wolf --region us-central1

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