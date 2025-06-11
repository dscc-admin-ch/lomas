# ADDING THE DATASET IN CONTAINER

# with PVC (persistent if container crashes)

first create pvc

```
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: lomas-pvc-gs
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Mi
```

kubectl apply -f lomas-pvc.yaml


Then patch the worker and server deployments with the new pvc

patch.yaml:
```
spec:
  template:
    spec:
      containers:
        - name: lomas-server
          volumeMounts:
            - name: data-volume
              mountPath: /data
      volumes:
        - name: data-volume
          persistentVolumeClaim:
            claimName: lomas-pvc-gs
```

kubectl patch deployment lomas-server --patch-file patch.yaml
kubectl patch deployment lomas-worker --patch-file patch.yaml


Then add the data in the pvc (copy folder data WITH datasets you want to add)


kubectl cp /home/onyxia/work/lomas/server/data/. lomas-server-d555f44d8-r4b9p:/data
kubectl cp /home/onyxia/work/lomas/server/data/. lomas-worker-55b9d45f88-vr4td:/data