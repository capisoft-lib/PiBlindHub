# Migration from the prototype

The previous repository contained several competing GPIO scripts and a Web process capable
of reaching hardware directly. They are removed from the active tree in this refactoring.
Do not run an old `sml`, `raspberryapp`, or `motorised-store.service` beside PiBlindHub.

The existing Raspberry calibration is evidence, not trusted input. Record its values before
uninstalling the old service, but re-measure both directions using the commissioning process.
Do not migrate an old position as sensor-confirmed; initialize it only through
`set_estimated_position`, or leave it unknown.

Migration is deliberately not automatic because service names, cron tasks, pin polarity,
and private configuration differ between prototype installations. Inventory them first:

```bash
systemctl list-unit-files | grep -Ei 'velux|blind|store|sml'
systemctl list-units --type=service --all | grep -Ei 'velux|blind|store|sml'
sudo crontab -l
crontab -l
sudo lsof /dev/gpiomem
```

Archive private files outside the repository, stop/disable the old owner, verify the pins
are inactive, then follow [Commissioning](COMMISSIONING.md). Do not delete the old data until
the new installation has passed acceptance and a rollback backup exists.
