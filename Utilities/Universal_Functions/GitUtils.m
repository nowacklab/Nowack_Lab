classdef GitUtils
    %GITUTILS Collection of static utilities used with git
    
    % Change log:
    % 15 09 18: Git works with LoggableObj and NIdaq through SQUID_IV
    
    methods(Static)
        function g = git(dir, author, headmesg, bodymesg) 
        % git(): run this to get status, add, commit, and record version
        % parameters: dir, message = strings
        % returns:    struct with parameters including version hash
            
            % for unusual case you want to disable git, here's a way of
            % doing it from the global scope
            global OVERRIDE_GITUTILS_GITOFF
            if (OVERRIDE_GITUTILS_GITOFF == 1)
                g = 'Git forcably disabled by global. NOT RECOMMENDED!!!';
                fprintf([g, '\n']);
                return;
            end
            
            status_old       = GitUtils.gitstatus(dir);
            add_cli_reply    = GitUtils.gitadd(dir);
            commitmessage    = [author, ': ', headmesg];
            commit_cli_reply = GitUtils.gitcommit(dir, commitmessage, bodymesg);
            status_new       = GitUtils.gitstatus(dir);
            version_hash     = GitUtils.gitrevhash(dir);
            g = struct('dir',                dir, ...
                       'status_old',         status_old,...
                       'add_cli_reply',      add_cli_reply,...
                       'commitmessage',      commitmessage,...
                       'commit_cli_reply',   commit_cli_reply,...
                       'status_new',         status_new,...
                       'version_hash',       version_hash...
                       );        
        end
        
        function str = gitrevhash(dir)
            old = cd(dir);
            [~, str] = system('git rev-parse HEAD');
            cd(old);
        end
        
        function str = gitstatus(dir)
            old = cd(dir);
            [~, str] = system('git status -s');
            cd(old);
        end
        
        function str = gitcommit(dir, message, bodymesg)
            old = cd(dir);
            [~, ~  ] = system(['cd ' dir]);
            [~, str] = system(['git commit -m "', message, '" -m ', ...
                                '"', bodymesg, '"']);
            cd(old);
        end
        
        function str = gitadd(dir)
            old = cd(dir);
            [~, ~  ] = system(['cd ' dir]);
            [~, str] = system(['git add ', dir]); %. works in subdirs
            cd(old);
        end
    end
end

