get_worksync_status() {
  date
  kubectl get worksync $1 -n flux-system -o json | jq '{
    name: .metadata.name,
    creationTimestamp: .metadata.creationTimestamp,
    reconciliationAttempted: .status.lastHandledReconcileAt,
    appliedRevision: .status.lastAppliedRevision,
    indexCreatedAt: .status.indexStatus.createdAt,
    indexModifiedAt: .status.indexStatus.modifiedAt,
    indexRevision: .status.indexStatus.indexRevision,
    indexStatus: .status.indexStatus.status,
    lastIndexStartedAt: .status.indexStatus.lastIndexStartedAt,
    lastIndexFinishedAt: .status.indexStatus.lastIndexFinishedAt,
    readyStatus: (
      ([.status.conditions[]? | select(.type == "Ready")] | first) as $ready |
      if $ready then ($ready.status + " | " + $ready.reason + " | " + $ready.lastTransitionTime) else "N/A" end
    ),
    reconcilingStatus: (
      ([.status.conditions[]? | select(.type == "Reconciling")] | first) as $reconciling |
      if $reconciling then ($reconciling.status + " | " + $reconciling.reason + " | " + $reconciling.lastTransitionTime) else "N/A" end
    ),
  }'
}

get_gitrepo_status() {
  date
  kubectl get gitrepository $1 -n flux-system -o json | jq '{
    name: .metadata.name,
    creationTimestamp: .metadata.creationTimestamp,
    reconciliationAttempted: .status.lastHandledReconcileAt,
    appliedRevision: .status.artifact.revision,
    artifactLastUpdateTime: .status.artifact.lastUpdateTime,
    readyStatus: (
      (.status.conditions[] | select(.type == "Ready")) as $ready |
        ($ready.status + " | " + $ready.reason + " | " + $ready.lastTransitionTime)),
    artifactInStorageStatus: (
      (.status.conditions[] | select(.type == "ArtifactInStorage")) as $artifact |
      ($artifact.status + " | " + $artifact.reason + " | " + $artifact.lastTransitionTime))
  }'

}

print_latest_slxs(){
    echo ---------`date`----------
    get_gitrepo_status $1
    get_worksync_status $1
    kubectl get servicelevelx -A --sort-by=.metadata.creationTimestamp -o jsonpath="{range .items[*]}{.metadata.creationTimestamp} {' '}{.metadata.name}{'\n'}{end}" | grep $1 | tail -5
}

list_worksync_status(){
    ctx=$1
    help_banner

    if [ -n "$ctx" ]; then
        kubectl_cmd="kubectl --context=$ctx"
    else
        kubectl_cmd="kubectl"
    fi
	echo -------`date`-------
	${kubectl_cmd} get worksync -A --sort-by=.metadata.name -o custom-columns=NAME:.metadata.name,lastHandledReconcileAt:.status.lastHandledReconcileAt,runbooks:.status.indexStatus.runbooksFound,indexStatus:.status.indexStatus.status,lastIndexStartedAt:.status.indexStatus.lastIndexStartedAt,lastIndexFinishedAt:.status.indexStatus.lastIndexFinishedAt,Type:.status.conditions[*].type,LastTransitionTime:.status.conditions[*].lastTransitionTime
}

connect_db(){
	help_banner
	password=`kubectl -n backend-services get secret core-pguser-core -o json | jq '.data.password'|base64 -d`
	stsname=`kubectl get statefulsets -n backend-services --no-headers | awk '/^core/ {print $1; exit}'`
	#kubectl exec -n backend-services -it statefulset/${stsname} -c database -- bash -c "PGPASSWORD=\"${password}\" psql -hlocalhost -Ucore -d core"
	kubectl exec -n backend-services -it statefulset/${stsname} -c database -- bash -c "PS1='[\u@\h \W \A]\$ ' PGPASSWORD=\"${password}\" psql -hlocalhost -Ucore -d core"
}

connect_db_ex() {
    ctx=$1
    help_banner

    if [ -n "$ctx" ]; then
        kubectl_cmd="kubectl --context=$ctx"
    else
        kubectl_cmd="kubectl"
    fi

    password=$($kubectl_cmd -n backend-services get secret core-pguser-core -o json | jq -r '.data.password' | base64 -d)
    stsname=$($kubectl_cmd get statefulsets -n backend-services --no-headers | awk '/^core/ {print $1; exit}')

    $kubectl_cmd exec -n backend-services -it statefulset/${stsname} -c database -- bash -c "PS1='[\u@\h \W \A]\$ ' PGPASSWORD=\"${password}\" psql -hlocalhost -Ucore -d core"
}

sli_cctag() {
  local context=""
  local workspace=""

  # Argument parsing
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --context)
        context="$2"
        shift 2
        ;;
      -w|--workspace)
        workspace="$2"
        shift 2
        ;;
      -*)
        echo "Unknown option: $1"
        usage
        return 1
        ;;
      *)
        echo "Unexpected argument: $1"
        usage
        return 1
        ;;
    esac
  done

  if [[ -z "$workspace" ]]; then
    echo "Error: -w|--workspace is required."
    usage
    return 1
  fi

  if [ -n "$context" ]; then
      kubectl_cmd="kubectl --context=$context"
  else
      kubectl_cmd="kubectl"
  fi

  $kubectl_cmd get servicelevelindicator -n default -l 'workspace=${workspace}' -o json | jq -c '.items[]|{"img":.status.image, "tag":.status.imageTag}' |sort | uniq -c
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
    echo "Command to list gcloud config"
    echo "gcloud config list"
    echo "sample working output"
    cat <<EOF
[core]
account = rohit.ekbote@runwhen.com
disable_usage_reporting = False
project = runwhen-dev-tiger
EOF

Your active configuration is: [default]
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
    echo "kubectl -n backend-services get secret core-pguser-core -o json | jq '.data.password'|base64 -d"
    echo "---------------------------------------------------------------------------------"
    echo "Get postgres credentials"
    echo "kubectl -n backend-services get secrets core-pguser-core -o 'go-template={{range \$k,\$v := .data}}{{printf \"%s: \" \$k}}{{if not \$v}}{{\$v}}{{else}}{{\$v | base64decode}}{{end}}{{\"\\n\"}}{{end}}'"
    echo "notes: Command assumes that your current context is platform cluster"
    echo "---------------------------------------------------------------------------------"
    echo "Forward postgres port to local machine"
    echo "kubectl -n backend-services port-forward svc/core-pgadmin 5050 --address=0.0.0.0"
    echo "notes: After this open http://localhost:5000" to open pgbouncer, username: core@pgo and password: recived in "kubectl -n backend-services get secrets core-pguser-core ..." command
    echo "---------------------------------------------------------------------------------"
    echo "Command to set reconciliation interval for all worksync instances as 60s"
    echo 'for ws in $(kubectl get worksync -A -o jsonpath="{.items[*].metadata.name}"); do kubectl patch worksync $ws -n flux-system --type=merge -p '{"spec":{"interval":"60s"}}'; done'
    echo "---------------------------------------------------------------------------------"
    echo "Command to list count of points in qdrant collection"
    cat <<EOF
    for c in \$(curl -s -X GET http://\$QDRANT_SERVICE_HOST:6333/collections | jq '.result.collections[] | select(.name | startswith(\"rdebug\")) | .name'); do d=\${c//\"/}; echo \$d \$(curl -s -X GET http://\$QDRANT_SERVICE_HOST:6333/collections/\$d | jq '.result.points_count'); done
EOF
    echo "notes: QDRANT_SERVICE_HOST is env var available in sobow-index"
    echo "---------------------------------------------------------------------------------"
    echo "Command to get modified time of qdrant collection"
    echo "kubectl exec -it qdrant-0 -c qdrant  -- stat --format '%n %y' /qdrant/storage/collections/rdebug-3k-02-blue--tasks"
    echo "---------------------------------------------------------------------------------"
    echo "Command to list index status of all worksyncs"
    echo "kubectl get worksync -A -o custom-columns=NAME:.metadata.name,lastHandledReconcileAt:.status.lastHandledReconcileAt,indexStatus:.status.indexStatus.status,lastIndexStartedAt:.status.indexStatus.lastIndexStartedAt,lastIndexFinishedAt:.status.indexStatus.lastIndexFinishedAt"
    echo "---------------------------------------------------------------------------------"
    echo "Query to list shard_no, workspace_name and slx count"
    echo "select coremodels_shard.shard_no, coremodels_workspace.name, count(1) from coremodels_slx inner join coremodels_workspace on coremodels_slx.workspace_id = coremodels_workspace.id inner join coremodels_shard on coremodels_shard.workspace_name = coremodels_workspace.name where coremodels_workspace.name like 'rdebug%' group by coremodels_shard.shard_no, coremodels_workspace.name order by coremodels_shard.shard_no, coremodels_workspace.name;"
    echo "---------------------------------------------------------------------------------"
    echo "Query to fetch count of runbooks having tasks populated"
    echo "SELECT w.name, COUNT(*) FROM coremodels_runbook r JOIN coremodels_slx s ON r.slx_id = s.id JOIN coremodels_workspace w ON s.workspace_id = w.id WHERE w.name like 'rdebug%' and r.body->'status'->'codeBundle'->'tasks'->>0 IS NOT NULL group by w.name order by w.name;"
    echo "---------------------------------------------------------------------------------"
    echo "Command to cleanup orphan SLXs"
    echo "kubectl -n backend-services exec deploy/papi -- python manage.py compare_slx --delete-orphaned-slx"
    echo "---------------------------------------------------------------------------------"
    echo "Command to list bucket files"
    echo "gcloud storage ls -l gs://runwhen-dev-tiger-shared-workspace/rdebug-small-07/--/**/stdout.txt"
    echo "---------------------------------------------------------------------------------"
}

help_banner

cd $SRC_BASE_PATH

export pandal=gke_runwhen-dev-panda_asia-south1_location-asia-south1-01
export pandap=gke_runwhen-dev-panda_asia-south1_platform-cluster
export tigerl=gke_runwhen-dev-tiger_northamerica-northeast2_location-northamerica-northeast2-01
export tigerp=gke_runwhen-dev-tiger_us-central1_platform-cluster
export tigerc=gke_runwhen-dev-tiger_us-central1_tiger-controlplane-cluster
export betap=gke_runwhen-nonprod-beta_us-west1_platform-cluster-01
export jpyel=gke_runwhen-nonprod-jpye_northamerica-northeast2_northamerica-northeast2-01
export jpyep=gke_runwhen-nonprod-jpye_us-central1_platform-cluster
export sandboxl=gke_runwhen-nonprod-sandbox_us-central1_sandbox-cluster-1-cluster
export testl=gke_runwhen-nonprod-test_northamerica-northeast1_location-01
export testp=gke_runwhen-nonprod-test_northamerica-northeast1_platform-cluster-01
export watcherp=gke_runwhen-nonprod-watcher_us-central1_platform-cluster
