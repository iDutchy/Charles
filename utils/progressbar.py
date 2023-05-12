start_fill = "<:pb_f_l:678984255493111868>"
center_fill = "<:pb_f_c:678984256344555528>"
end_fill = "<:pb_f_r:678984256084639745>"

start_empty = "<:pb_e_l:678982030263844872>"
center_empty = "<:pb_e_c:678983220745732116>"
end_empty = "<:pb_e_r:678982019849388052>"

def create(end=100, x_per=10, value=30):
    bar = ""
        
    if x_per > end:
        raise ValueError("'x_per' can not be higher than 'end value'!")

    if value > end:
        raise ValueError("'value' can not be higher than 'end value'!")

    total = int((end/x_per))
    total_filled = int(value/x_per)
    total_empty = int(total-total_filled)


    if total_filled == 0:
        bar += start_empty
    else:
        bar += start_fill

    if total_filled != total:
        total_center_fill = total_filled -1
    else:
        total_center_fill = total_filled

    if total_center_fill > 0:
        bar += center_fill * total_center_fill

    if total_empty >= 1:
        if total_empty == 1:
            total_center_empty = total_empty -1
        else:
            total_center_empty = total_empty
        bar += center_empty * total_center_empty

    if total_empty >= 1:
        bar += end_empty
    if total_empty == 0:
        bar += end_fill

    return bar

