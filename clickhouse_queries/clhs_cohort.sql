select 
    cohort,
    days_distance,
    uniqExact( DeviceID) as devices
from
  (  
select
    l.AppPlatform as AppPlatform,
    l.events as events,
    cast(l.EventDate as date) as EventDate,
    l.DeviceID as DeviceID,
    r.birthday as birthday,
    cast(l.EventDate as date) - r.birthday as days_distance
from events as l
left join 
    (
    select
        DeviceID,
        min(cast(EventDate as date)) as birthday
    from events 
    where AppPlatform == 'iOS'
    group by DeviceID
    ) as r
        on l.DeviceID=r.DeviceID
where l.AppPlatform == 'iOS'
)
where 
    days_distance <= 10 and
    birthday <= cast('2019-01-10' as Date)
group by birthday as cohort,
days_distance
order by cohort asc, 
days_distance asc
limit 1000

DRAW_HEATMAP
"days_distance.cohort.devices"