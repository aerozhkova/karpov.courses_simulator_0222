select
    days_distance,
    uniqExact( DeviceID) / 4298120.0 * 100 as devices
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
group by days_distance
order by days_distance