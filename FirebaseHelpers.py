import firebase_admin


# firebase queries returns lists (when # return > 1)
# This function converts them into dictionaries.
# Dictionaries can then be converted to JSON and returned to frontend.
def getDictFromList(result):
    records = {}
    for i in range(len(result)):
        item = result[i].to_dict()
        records[i] = {}
        for key in item:
            #  some firebase data types are not JSON serializable, 
            #  so we must take necessary info out of the objects to feed our return json object     
            if isinstance(item[key], firebase_admin.firestore.GeoPoint):
                records[i][key] =str(item[key].latitude)+','+str(item[key].longitude)
                continue
            if isinstance(item[key], firebase_admin.firestore.DocumentReference):
                print(type(item[key]))
                records[i][key] = item[key].id
                continue
            records[i][key] = item[key]
        records[i]["id"] = result[i].id
        
    return records