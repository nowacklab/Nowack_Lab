function check_currents(Isquid, Imod)
% prevents accidental SQUIDicide

    if Isquid > 100e-6 || Imod > 300e-6
        error('Current too high! Don''t kill the squid!')
    end
end
