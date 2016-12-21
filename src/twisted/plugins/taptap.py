from twisted.application.service import ServiceMaker

serviceMaker = ServiceMaker('taptap',
                            'taptap.service',
                            'Personal writing statistics.',
                            'taptap')
