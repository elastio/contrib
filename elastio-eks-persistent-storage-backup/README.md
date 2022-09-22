# Amazon EKS persistent storage backup, vulnerability scan and restore

---

## Requirements
- AWS CLI
- elastio CLI
- kubectl CLI

## Backup procedure
Backup and vulnerability scan of EBS persistent storage can be done by schedule via WEB UI or manually via elastio CLI.

### Backup in WEB UI
1. Login to your elastio tenant
2. Press `+ New policy` button on Policies page
3. Specify policy name and schedule
4. Enable `Scan for Ransomware` and `Scan for Malware` options
5. Select EBS persistent storage in asset list available for backup
6. Save and run new policy

### Backup in elastio CLI
To backup EBS persistent storage via elastio CLI use next command:
```
elastio ebs backup --volume-id <volume ID>
```

Use `--iscan` option to run vulnerability scan immediately after backup.

## Restore procedure
As a result of backup a recovery point will be created. You can find newly created recovery point and its scan status in WEB UI by following asset name link. Or as output of `elastio ebs backup` command.
![image](https://user-images.githubusercontent.com/81738703/191742622-1f353813-8216-4a5e-830e-538964f0f10f.png)

### Restore in WEB UI
1. Login to your elastio tenant
2. Open Assets page and click on asset you would like to restore
3. In the list of recovery points open context menu of recovery point and press `Restore`
4. Press `Restore from here` button
![image](https://user-images.githubusercontent.com/81738703/191743839-bcd28739-998e-47e0-bf19-3de7b4d51b8b.png)

### Restore in elastio CLI
To restore EBS persistent storage via elastio CLI use next command:
```
elastio ebs restore --rp <recovery pint ID>
```

When restore job is finished new EBS volume will be created in AWS.

## Configure a pod to use restored EBS as persistent volume

### Create a PersistentVolume
```
kubectl apply -f pv-volume.yaml
```

Configuration file for the PersistentVolume:
```
apiVersion: v1
kind: PersistentVolume
metadata:
  name: <Persistent Volume Name>
spec:
  accessModes:
  - ReadWriteOnce
  awsElasticBlockStore:
    fsType: ex4
    volumeID: <Volume ID>
  capacity:
    storage: 16Gi
  storageClassName: <Storage Class Name>
  volumeMode: Filesystem
```
Replace `<Persistent Volume Name>`, `<Storage Class Name>`, `<Volume ID>` with your values, also specify correct storage size and file system type.

View information about the PersistentVolume:
```
kubectl get pv <Persistent Volume Name>
```

### Create a PersistentVolumeClaim
```
kubectl apply -f pv-claim.yaml
```
Configuration file for the PersistentVolumeClaim:
```
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: <Persistent Volume Claim Name>
spec:
  storageClassName: <Storage Class Name>
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 3Gi
```
Replace `<Persistent Volume Claim Name>`, `<Storage Class Name>` with your values, also specify correct storage size.

### Edit PODs configuration file
1. Run the `kubectl edit pod <pod name>` command.
2. Change options below with your values:
```
spec:
  volumes:
    - name: <Persistent Volume Name>
      persistentVolumeClaim:
        claimName: <Persistent Volume Claim Name>
  containers:
      volumeMounts:
        - mountPath: "<Mount Path>"
          name: <Persistent Volume Name>
```
3. Run new Pod with updated configuration file
