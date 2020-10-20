import firebase_admin

def getDictFromList(result):
    records = {}
    for i in range(len(result)):
        item = result[i].to_dict()
        records[i] = {}
        for key in item:
            if isinstance(item[key], firebase_admin.firestore.GeoPoint):
                records[i][key] =str(item[key].latitude)+','+str(item[key].longitude)
                continue
            if isinstance(item[key], firebase_admin.firestore.DocumentReference):
                print(type(item[key]))
                records[i][key] = item[key].id
                continue
            records[i][key] = item[key]
        
    return records