from odoo import fields, models
import datetime

def calc_working_minutes(check_in,check_out):
    
    if  not check_in and not check_out:
        return
    
    start = datetime.datetime.strptime(check_in,"%Y-%m-%d %H:%M:%S")
    end = datetime.datetime.strptime(check_out,"%Y-%m-%d %H:%M:%S")
    difference = end - start
    minutes = difference.total_seconds() / 60
    return int(minutes)

def calc_working_hours(mins):
    hr = mins/60.0
    
    hr,mint = divmod(hr,1)
    mint = (round(mint*60))/100
    hours = hr+mint
    return hours

def check_ok_status(policy):
    
    diff =0
    t=0
    for cok in policy:
        if cok.status == '0':
            time = str(cok.time_to).split(".")

            t = int(time[1])
            if int(time[1]) < 5:
                t = int(time[1])*10
           
            diff = ((int(time[0])))*60 + t
    return diff

def calc_standard_hrs(working_hours):
    standard_hours = 0.0
    
    if working_hours.uom_id.factor:
        hours = str(working_hours.uom_id.factor).split(".")
        standard_hours = (float(hours[0])*60)+float(hours[1])
    
    return standard_hours

def time_in_out(t):
    time = str(t.time()).split(":")
    tm = time[0]+'.'+time[1]
    tm = (float(tm))+5
    
    return tm

def check_in_out_status(time,policy):
    status =''
    for t in policy:
        if time >= t.time_from and time <= t.time_to:
            status= t.status
    return status

def calc_minutes(time):
   
    actual_minutes = ((int(time[0]))+5)*60 + int(time[1])
    return actual_minutes


class HrAttendenceInherit(models.Model):
    
    _inherit = 'hr.attendance'
    
    machine_check_in = fields.Datetime("New Check In")
    machine_check_out = fields.Datetime("New Check Out")
    
    def _my_request(self):
        
        if self.change_request:
            self.request_created = True
        else:
            self.request_created = False
            
    change_request = fields.Many2one('my.change.request',string="Change Request")
    request_created = fields.Boolean(compute='_my_request')
    
    def updateRecord(self):
       
        if self.machine_check_in or self.machine_check_out:
            a = self.machine_check_in
        
            a = datetime.datetime.strptime(a,"%Y-%m-%d %H:%M:%S").date()

        
            check_in = self.machine_check_in
            check_out = self.machine_check_out
            compensatory = 'no'
            compensatory_leave = 0
            overtime_in_hr = 0        
            workingtime_in_hr = 0
            normal_working_hours = 0
            sch_time = 0
            overtime = 0
            cur_day =a.weekday()
            working_day = 'no'
            h = 'present'
        
            sch_time = 0
            if cur_day == 6: ## Sunday off day
                h = 'off_day'
            
            emp_working_hour = self.machine_shift
            
            if emp_working_hour:
                in_policy = emp_working_hour.in_policy_id
                out_policy = emp_working_hour.out_policy_id
                working_time = emp_working_hour.attendance_ids
                compensatory_hrs = emp_working_hour.compensatory_hours
                
                ## Working Hours ##
                
                if check_in and check_out:
                    working_time_in_min = calc_working_minutes(check_in,check_out)
                    workingtime_in_hr = calc_working_hours(working_time_in_min)
                    
                    start = datetime.datetime.strptime(check_in,"%Y-%m-%d %H:%M:%S")
    
                    end = datetime.datetime.strptime(check_out,"%Y-%m-%d %H:%M:%S")

                ## Standard Hours ##
                    
                    standard_hours = 0
                    sch = ''
                    sch_out_time =''
                    sch_out = 0.0
                    day = start.date().weekday()
                    standard_hours = calc_standard_hrs(emp_working_hour)
                    for w in working_time:
                        if w.dayofweek == str(day):
                            working_day = 'yes'
                            sch_time = w.hour_from
                            mint = (sch_time*60)% 60
                            sch = str(sch_time).split(".")
                            sch_time = int(sch[0])*60 + int(mint)
                            sch_out = w.hour_to
                            mint = (sch_out*60)%60
                            sch_out_time = str(sch_out).split(".")
                            sch_out = int(sch_out_time[0])*60 + int(mint)
                
                    ## Overtime ##
                  
                    extra_day = 'no'
                    overtime = working_time_in_min - standard_hours
                    if overtime > 0:
                        overtime_in_hr = overtime/60
                      
                    ## Normal Working Hours ##
                      
                    normal_working_hours = int(workingtime_in_hr) - int(overtime_in_hr)
                      
                    ## Extra Day ##
                  
                    if working_day == 'no':
                        extra_day = 'yes'
                        h='off_day'
                        
                        ## Compensatory ##
                      
                        if h=='off_day' and working_time_in_min >= compensatory_hrs * 60 :
                            compensatory = 'yes'
                            compensatory_leave = 1
                    
                    maximum = ''
                    in_status_value=0
                    out_status_value=0
                    out_time_in_hours = 0.0
                    late_in_time_hours = 0.0
                    late_in_time = 0.0
                    penalty = 0.0
                    early_time_out = 0.0
                    in_status=''
                    out_status=''
                    diff = 0.0
                    actual_minutes = 0
                    lt = 0
                    attendance_status =0  
                    temp=0
                    
                    ## Late Time in and In Status ##
                  
                    if working_day == 'yes':
                        latetimein = str(start.time()).split(":")
                        actual_minutes = calc_minutes(latetimein)
                          
                        diff = (actual_minutes - sch_time)
                          
                        diff = calc_working_hours(diff)
                        lt = check_ok_status(in_policy)
                        temp =actual_minutes - sch_time
                         
                        late_in_time = (actual_minutes - sch_time)-int(lt)
                        
                        late_in_time_hours = calc_working_hours(temp)
                        in_status = check_in_out_status(late_in_time_hours,in_policy)
                        
                        
                        if late_in_time < 0:
                            late_in_time = 0
                          
                        penalty = late_in_time * 2
                  
                  
                    # Early Time out and Out Status ##
                  
                    if working_day == 'yes':
                        out_time_in_hours = workingtime_in_hr
                        out_status = check_in_out_status(out_time_in_hours,out_policy)
                       
                        if out_status == '1':
                            early_time_out =abs(overtime)
                      
                    # Attendance Status ##
                    
                        in_status_value = in_status
                        out_status_value = out_status
                        maximum = max(in_status_value,out_status_value)
                          
                        attendance_status = maximum
                      
                   
                self.working_hours = working_time_in_min
                self.workingtime_in_hr = workingtime_in_hr
                self.standard_hours = standard_hours
                self.over_time = overtime
                # self.over_time_hr = overtime_in_hr
                self.normal_working_hours = normal_working_hours
                self.late_in_time = late_in_time
                self.penalty = penalty
                self.in_status = in_status
                self.early_time_out = early_time_out
                self.out_status = out_status
                self.attendance_status = attendance_status
                self.extra_day = extra_day
                self.compensatory = compensatory
                self.compensatory_leave = compensatory_leave
                self.status = h