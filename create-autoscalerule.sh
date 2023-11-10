resourceGroup="acdnd-c4-project"
vmssName="udacity-vmss"
autoscalerulename="autoscaleName"

echo "login into azure"
az login

echo "STEP 0 - Creating Scale Rule"
az monitor autoscale create \
  --resource-group $resourceGroup \
  --resource $vmssName \
  --resource-type Microsoft.Compute/virtualMachineScaleSets \
  --name $autoscalerulename \
  --min-count 2 \
  --max-count 10 \
  --count 2

  echo "STEP 1 - Creating a rule to autoscale out"

  az monitor autoscale rule create \
  --resource-group $resourceGroup \
  --autoscale-name $autoscalerulename \
  --condition "Percentage CPU > 70 avg 5m" \
  --scale out 3

  echo "STEP 2 - Creating a rule to autoscale in"

  az monitor autoscale rule create \
  --resource-group $resourceGroup \
  --autoscale-name $autoscalerulename \
  --condition "Percentage CPU < 30 avg 5m" \
  --scale in 1