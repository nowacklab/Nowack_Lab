function ramped = IVramp(param, down)
    if nargin < 2
        down = true;
    end

    half = param.Irampmin:param.Irampstep:param.Irampmax;
    if down
        ramped = [half flip(half)]* param.Rbias; % ramp up then down
    else
        ramped = half * param.Rbias;
    end
    
end