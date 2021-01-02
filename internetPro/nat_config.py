import telnetlib
import re


global_settings = NatSettings()


def valid_ip(ip):
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    parts = [int(p) for p in parts]
    for p in parts:
        if p < 0 or p > 255:
            return False
    return True


def valid_mask(mask):
    parts = mask.split('.')
    if len(parts) != 4:
        return False
    parts = [int(p) for p in parts]
    for p in parts:
        if p < 0 or p > 255:
            return False
    m = _convert_v4(mask)
    k = 0
    for i in range(32):
        j = m & (1 << i)
        if k == 0 and j != 0:
            k = 1
        elif k == 1 and j == 0:
            return False
    return True


def same_net(ip1, mask1, ip2, mask2):
    if mask1 != mask2:
        return False
    ip1 = _convert_v4(ip1)
    mask1 = _convert_v4(mask1)
    ip2 = _convert_v4(ip2)
    mask2 = _convert_v4(mask2)
    return ip1 & mask1 == ip2 & mask2


def _convert_v4(v4):
    parts = [int(p) for p in v4.split('.')]
    return parts[0] * (1 << 24) +\
           parts[1] * (1 << 16) +\
           parts[2] * (1 << 8) +\
           parts[3]


def _int_to_v4(int_v4):
    return '.'.join([str(((int_v4 << i) % (1 << 32)) >> 24) for i in range(0, 32, 8)])


class NatSettings:
    def __init__(self):
        self.rta = {
            's0/0/0': {
                'ip': '192.168.1.2',
                'mask': '255.255.255.252'
            },
            'f0/0': {
                'ip': '10.0.0.1',
                'mask': '255.0.0.0'
            },
            'c': 's0/0/0'
        }
        self.rtb = {
            's0/0/0': {
                'ip': '192.168.1.1',
                'mask': '255.255.255.252'
            },
            'f0/0': {
                'ip': '192.168.3.1',
                'mask': '255.255.255.0'
            },
            'c': 's0/0/0'
        }
        self.rtc = {
            'f0/0': {
                'ip': '10.0.0.2',
                'mask': '255.0.0.0'
            },
            'c': 'f0/0'
        }
        self.xyz_net = {
            'ip': '192.168.1.32',
            'mask': '255.255.255.224'
        }
        self.host_a = {
            'ip': '10.0.0.11',
            'mask': '255.0.0.0'
        }
        self.host_b = {
            'ip': '192.168.3.2',
            'mask': '255.255.255.0'
        }
        self.login_passwd = 'CISCO'
        self.enable_passwd = 'CISCO'

        self.use_static = True
        self.static_nat = {
            self.rtc['f0/0']['ip']: '192.168.1.34',
            self.host_a['ip']: '192.168.1.35',
        }
        
        self.err_msg = ''

    def validate(self):
        pass


def nat_config():
    settings = global_settings
    atn = _init(settings.rta[settings.rta['c']]['ip'],
                settings.login_passwd,
                settings.enable_passwd)
    for intn in settings.rta:
        if intn != 'c' and intn != settings.rta['c']:
            _config_int(atn, intn, settings.rta[intn])

    btn = _init(settings.rtb[settings.rtb['c']]['ip'],
                settings.login_passwd,
                settings.enable_passwd)
    for intn in settings.rtb:
        if intn != 'c' and intn != settings.rtb['c']:
            _config_int(btn, intn, settings.rtb[intn])

    ctn = _init(settings.rtc[settings.rtc['c']]['ip'],
                settings.login_passwd,
                settings.enable_passwd)

    # Step 1. Basic ip address config.
    # 1.1 RTA
    _inputln(atn, 'conf t')
    _read_until(atn, 'Router(config)#'))
    _inputln(atn, 'ip route 0.0.0.0 0.0.0.0 %s' % settings.rtb['s0/0/0']['ip'])
    _read_until(atn, 'Router(config)#')
    # 1.2 RTB
    _inputln(btn, 'conf t')
    _read_until(btn, 'Router(config)#')
    _inputln(btn, 'ip route %s %s %s' % (settings.xyz_net['ip'], settings.xyz_net['mask'], settings.rta['s0/0/0']['ip']))
    _read_until(btn, 'Router(config)#')
    # 1.3 RTC
    _inputln(ctn, 'conf t')
    _read_until(ctn, 'Router(config)#')
    _inputln(ctn, 'ip route 0.0.0.0 0.0.0.0 %s' % settings.rta['f0/0']['ip'])
    _read_until(ctn, 'Router(config)#')
    _inputln(ctn, 'end')
    _read_until(ctn, 'Router#')
    # 1.4 Test connection.
    _inputln(atn, 'end')
    _read_until(atn, 'Router#')
    if _test_ping(atn, settings.host_a['ip']) < .5:
        return False, 'Failed to ping host A from RTA after step 1.'
    if _test_ping(atn, settings.host_b['ip']) < .5:
        return False, 'Failed to ping host B from RTA after step 1.'

    # Step 2. NAT config.
    _inputln(atn, 'conf t')
    _read_until(atn, 'Router(config)#')
    if settings.use_static:
        # 2.1-1 Static NAT.
        for src_ip in settings.static_nat:
            _inputln(atn, 'ip nat inside source static %s %s' % (src_ip, settings.static_nat[src_ip]))
            _read_until(atn, 'Router(config)#')
    else:
        # 2.1-2 Dynamic NAT
        clear_static_nat_config(atn, settings)
        _inputln(atn, 'ip nat pool globalXYZ %s %s netmask %s' % (
            _get_first_ip(settings.xyz_net['ip'], settings.xyz_net['mask']), 
            _get_last_ip(settings.xyz_net['ip'], settings.xyz_net['mask']),
            settings.xyz_net['mask']
        ))
        _read_until(atn, 'Router(config)#')
        _inputln(atn, 'access-list 1 permit %s %s' % (
            _int_to_v4(_convert_v4(settings.rta['f0/0']['ip']) & _convert_v4(settings.rta['f0/0']['mask'])),
            _int_to_v4(~_convert_v4(settings.rta['f0/0']['ip']) % (1 << 32))
        ))
        _read_until(atn, 'Router(config)#')
        _inputln(atn, 'ip nat inside source list 1 pool globalXYZ overload')
        _read_until(atn, 'Router(config)#')
    # 2.2 Interface delegation.
    _inputln(atn, 'int f0/0')
    _read_until(atn, 'Router(config-if)#')
    _inputln(atn, 'ip nat inside')
    _read_until(atn, 'Router(config-if)#')
    _inputln(atn, 'int s0/0/0')
    _read_until(atn, 'Router(config-if)#')
    _inputln(atn, 'end')
    _read_until(atn, 'Router#')
    # 2.3 Test connection.
    if settings.use_static:
        if _test_ping(ctn, settings.host_b['ip']) < .5:
            return False, 'Failed to ping host B from RTC after step 2.'

    return True, 'Success.'


def clear_static_nat_config(tn, settings):
    for private_ip, public_ip in settings.static_nat.items():
        _inputln(tn, 'no ip nat inside source static %s %s', (private_ip, public_ip))
        _read_until(tn, 'Router(config)#')


def get_translations():
    settings = global_settings
    atn = _init(settings.rta[settings.rta['c']]['ip'],
                settings.login_passwd,
                settings.enable_passwd)
    return ''


def get_statistics():
    return ''


def _get_first_ip(net_ip, net_mask):
    ip_0 = _convert_v4(net_ip)
    return _int_to_v4(ip_0 + 1)


def _get_last_ip(net_ip, net_mask):
    ip_0 = _convert_v4(net_ip)
    mask_v = _convert_v4(net_mask)
    return _int_to_v4((ip_0 | (~mask_v) % (1 << 32) - 1))


def _test_ping(tn, ip):
    _inputln(tn, 'ping %s' % ip)
    s = _read_until(tn, 'Router#', timeout=12)
    p = 'Success rate is (\\d+) percent'
    rate = int(re.findall(p, s)[0]) / 100
    return rate


def _config_int(tn, int_name, ip_mask):
    _inputln(tn, 'conf t')
    _read_until(tn, 'Router(config)#')
    _inputln(tn, 'int %s' % int_name)
    _read_until(tn, 'Router(config-if)#')
    _inputln(tn, 'ip address %s %s' % (ip_mask['ip'], ip_mask['mask']))
    _read_until(tn, 'Router(config-if)#')
    _inputln(tn, 'no shut')
    _read_until(tn, 'Router(config-if)#')
    _inputln(tn, 'end')
    _read_until(tn, 'Router#')


def _inputln(tn, txt):
    tn.write(('%s\n' % txt).encode())


def _read_until(tn, til, timeout=None):
    return tn.read_until(til.encode(), timeout=timeout)


def _init(host, login_passwd, enable_passwd):
    tn = telnetlib.Telnet(host)
    _read_until(tn, 'Password: ')
    _inputln(tn, login_passwd)
    _read_until(tn, 'Router>')
    _inputln(tn, 'enable')
    _read_until(tn, 'Password: ')
    _inputln(tn, enable_passwd)
    _read_until(tn, 'Router#')
    return tn


def main():
    host = '10.0.0.3'
    tn = telnetlib.Telnet(host)
    print(tn.read_until(b'Password: '))
    tn.write(b'cisco\n')
    print(tn.read_until(b'Router>'))
    tn.write(b'enable\n')
    print(tn.read_until(b'Password: '))
    tn.write(b'cisco\n')
    print(tn.read_until(b'Router#'))
    tn.write(b'show int\n')
    res = tn.read_until(b'Router#', timeout=1).decode()
    while res.find('Router#') < 0:
        tn.write(b' ')
        res += tn.read_until(b'Router#', timeout=1).decode()
    print(res)
