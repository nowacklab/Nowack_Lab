function squid_prompt(no_squid)

if no_squid
    prompt = input('No SQUID present. Correct? y/n [y]: ','s');
    if ~(isempty(prompt) || prompt=='y' || prompt=='Y')
        error('Edit the no_squid=true line!');
    end
end

end