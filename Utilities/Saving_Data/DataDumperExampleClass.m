classdef LoggableObj_mock_instrument < LoggableObj

properties (Access = public)
    newprop 
    newprop2
end

methods (Access = public)
    function this = LoggableObj_mock_instrument(name, dir)
        this = this@LoggableObj(name, dir);
        this.newprop = 10;
        this.newprop = 11;
    end

    function delete(this)
        this.delete@LoggableObj();
        clear this.newprop;
    end 

    function [paramname, savename] = savetestdata(this, data, header)
        paramname = this.saveparams({'newprop','newprop2'});
        savename  = this.savedata  (data, header);
    end
end
end



