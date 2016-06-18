function param_prompt(paramfile)

prompt = input(strcat('Parameter file is: ',paramfile,'\nContinue? y/n [y]: '),'s');
if ~(isempty(prompt) || prompt=='y' || prompt=='Y')
    error('Check those params');
end

end