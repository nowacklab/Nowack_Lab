classdef LoggableObj < handle % {
    
    
% 15 09 17: Fix the populategit method -DL
properties (Access = public)
    notes   % NOTES to save
    p       % Parameters to save
    lastdatasave = '' %last data  save file name
    lastparamsave= '' %last param save file name
    scantype     = '' % extra notes to save what kind of scan this was
    savedir
end

properties (Access = protected)
    git
    namestring
    author
end

properties (Constant)
    FILEPATH   = 'modules/LoggableObj.m'; %for git logging
    GITHEAD    = 'Automatic LoggableObj Commit';
end

methods (Access = public)% {

    function this = LoggableObj(name, author, savedirectory)
        this.git            = '';
        this.notes          = '';
        this.namestring     = name;
        this.savedir        = savedirectory;
        this.author         = author;
    end

    function delete(this)
        clear this.git;
        clear this.notes;
        clear this.p;
        clear this.namestring;
        clear this.savedir;
        clear this.author;
    end

end 

methods (Access = protected)

    function filename = saveparams(this, keys)
    % this.saveparams(keys), saves all keys into paramaters file + git
        
        % Sanitizes path name so I know where libraries repo is
        path = which(mfilename);
        filepath = regexprep(this.FILEPATH, '[/\\]', '\\\\');
        path = regexprep(path, [filepath, '$'], '');
        
        this.git = GitUtils.git(path, ...
                        this.author, ...
                        ['[',this.namestring,'] ', this.GITHEAD],...
                        this.notes);
                    
        % making & populating parameters struct to save            
        parameters = struct(this.namestring, struct());
        keys = [keys, {'git', 'namestring', 'savedir', 'notes', 'p',}];
        for i = 1:length(keys)
            parameters.(this.namestring).(keys{i}) = this.(keys{i});
        end
        
        filename = [this.savedir, this.paramstring()];
        this.lastparamsave = filename;
        
        save(filename, '-struct', 'parameters');
    end

    function filename = savedata(this, datamatrix, header)
    % file name = this.savedata(data in matrix, header label string)
    
        filename = [this.savedir, this.datastring()];
        this.lastdatasave = filename;
        
        CSUtils.savecsv(filename, datamatrix, header);
    end

end 

methods (Access = private)
    function datastr = datastring(this)
        datastr = [this.timestring, '_', ... 
                   this.namestring, '_', ...
                   this.scantype, '_', ...
                   'data.csv'];
    end

    function paramstr = paramstring(this)
        paramstr = [this.timestring, '_', ...
                    this.namestring, '_', ...
                    this.scantype, '_', ...
                    'params.mat'];
    end

end % }end private methods

methods (Static)
     function str = timestring()
        str = char(datetime('now','TimeZone','local','Format',...
                                'yyyyMMdd_HHmmss_z'));
     end
end

end % }end of classdef
