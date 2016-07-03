import json;

class SaverError(Exception):
    def __init__(self, value):
        self.value=value;
    def __str__(self):
        return repr(self.value);

class LoadError(Exception):
    def __init__(self, value):
        self.value=value;
    def __str__(self):
        return repr(self.value);

class Saver:
    def __init__(self):
        self.__myid = id(self);
        #self.__class = str(self.__class__)
        self.__class = str(self.__class__.__name__)
        return;

    def load(self, dictionary):
        self.__dict__ = dictionary;
        return;

    #INCOMPLETE
    # dictionary is the dictionary that defines the object
    # oldobjdict is a dictionary where the keys are the old 
    #   (when the state was saved) id of the object and the 
    #   value is a reference to the new object

    def linkingload(self, dictionary, oldobjdict, missingobj):
        from attoclass import Atto
        from daqclass import DAQ
        from sweepclass import Sweep

        try:
            oldme = dictionary['_Saver__myoldid'];
        except:
            print(dictionary);

        #to end recursion
        if (oldme in oldobjdict.keys()):
            raise LoadError(oldme);

        # I am loading this object now.  Put in the dict of 
        # old objects
        oldobjdict[oldme] = self;
        

        for k in dictionary.keys():
            try:
                dictionary[k].keys();
            except:
                #If it gets here, it is not an object! or its one we don't 
                # know how to deal with

                #Don't save stupid things that don't make sense for this
                #object or are redundant
                if(k == '_Saver__class' or 
                   k == '_Saver__myid'  or 
                   k == '_Saver__myoldid'):
                    continue;
                self.__dict__[k] = dictionary[k];
                continue;
                
            if (list(dictionary[k].keys())[0] == 'NEW OBJECT'):
                # Based on the saved data, figure out what object 
                # needs to be made and make it
                exec('self.__dict__[k] = ' + 
                    dictionary[k]['NEW OBJECT']["_Saver__class"] + 
                    '()');

                # Run this function on that object.
                # That means that by the end, obj object and any subobjects
                # are created.  Any new objects are in oldobjdict.  Any
                # unknown objects are added in missingobj
                [oldobjdict, 
                 missingobj] = self.__dict__[k].linkingload(
                                    dictionary[k]['NEW OBJECT'],
                                    oldobjdict, missingobj);
                continue;

            if (list(dictionary[k].keys())[0] == 'EXISTING OBJECT'):
                #If the saver did not save this objects information 
                #  (because it has already saved it once and we don't want
                #  multiple copies of the same object)
                # Then 

                oldid = dictionary[k]['EXISTING OBJECT'];

                # Check if the object is in oldobjdict (meaning I've 
                # already made it)
                if(oldid in oldobjdict.keys()):
                    #If true, link (oldobjdict contains refs to objs)!!!
                    self.__dict__[k] = oldobjdict[oldid]
                    continue;

                # Now, the object I want hasn't been loaded yet.  So, I 
                # need to store exactly where I am right now so at the end
                # I can find these and fix them
                newentry = [self, dictionary[k]];

                #If other current objects cannot find the same old object 
                # I can't find, append my entry to that list.  Else, make 
                # a new list
                if (oldid in missingobj.keys()):
                    missingobj[oldid] = missingobj[oldid].append(newentry);
                else:
                    missingobj[oldid] = [newentry];

                continue;

            print(list(dictionary[k].keys())[0] == 'NEW OBJECT');
            print(list(dictionary[k].keys())[0]);
            raise LoadError(k);

                
        # For each missing object id,
        for oldid in missingobj.keys():
            #If the old ID is in the oldobjdict 
            # (meaning I've made that object)
            if(oldid in oldobjdict.keys()):
                # Go through each element of missing obj and link the
                # objects to the references
                for entry in missingobj[oldid]:
                    entry[0].__dict__[entry[1]] = oldobjdict[oldid];
                # Then, delete this entry in missingobj because all 
                # of it is fixed!
                del(missingobj[oldid]);

        return [oldobjdict, missingobj]






    #Recursively converts the object into a dict
    #only behaves well if objs in this class inherent Saver
    def todict(self, savedobjs):

        me = self.__myid;

        # To end recursion
        if (me in savedobjs):
            raise SaverError(me);

        # I am saving this object now.  Put into the list of saved
        # objects so I don't try and save it again
        savedobjs.append(me);

        # for loading
        self.__myoldid = me;

        dictofme = {};
        allvars = self.__dict__;
        for key in allvars.keys():
            try:
                # If this key is an object, run todict on this object
                # and update the saved objects list
                [objdict, savedobjs] = allvars[key].todict(savedobjs);

                # Make sure the load knows this is a new object
                objdict = {'NEW OBJECT': objdict}

            except SaverError as e:
                # If the object was already saved, we need to record
                # the id of the object so we can link in load
                objdict = {'EXISTING OBJECT': allvars[key].__myid};

            except:
                #this is not an object I know how to deal with
                try:
                    #emergency storage, just in case!  Loading will
                    #just load this as a dictionary of crap
                    objdict = allvars[key].__dict__;

                except:
                    #this is not an object
                    objdict = allvars[key];

            dictofme[key] = objdict;

        return [dictofme, savedobjs];

    @staticmethod
    def tojson(dictionary):
        return json.dumps(dictionary, sort_keys=True, indent=4,
                separators=(',', ': '));

    @staticmethod
    def fromjson(js):
        return json.loads(js);

    
    @staticmethod
    def tocommentjson(dictionary, commentchar='#'):
        j = Saver.tojson(dictionary);
        js = j.splitlines();
        forfile = '';
        for i in range(len(js)):
            forfile = forfile + '# ' + js[i] + '\n';
        return forfile;

