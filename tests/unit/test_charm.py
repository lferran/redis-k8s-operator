# This file is part of the Redis k8s Charm for Juju.
# Copyright 2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import unittest
from unittest import mock

from oci_image import OCIImageResource, OCIImageResourceError
from ops.model import ActiveStatus, WaitingStatus, MaintenanceStatus, BlockedStatus
from ops.testing import Harness

from charm import RedisCharm
from charms.redis_k8s.v0.redis import RedisProvides
from client import RedisClient


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(RedisCharm)
        self.addCleanup(self.harness.cleanup)
        redis_resource = {
            "registrypath": "ubuntu/redis"
        }
        self.harness.add_oci_resource("redis-image", redis_resource)
        self.harness.begin()

    def test_on_start_when_unit_is_not_leader(self):
        # Given
        self.harness.set_leader(False)
        # When
        self.harness.charm.on.start.emit()
        # Then
        self.assertEqual(
            self.harness.charm.unit.status,
            ActiveStatus()
        )

    @mock.patch.object(RedisClient, 'is_ready')
    def test_on_start_when_redis_is_not_ready(self, is_ready):
        # Given
        self.harness.set_leader(True)
        is_ready.return_value = False
        # When
        self.harness.charm.on.start.emit()
        # Then
        is_ready.assert_called_once_with()
        self.assertEqual(
            self.harness.charm.unit.status,
            WaitingStatus("Waiting for Redis ...")
        )

    @mock.patch.object(RedisClient, 'is_ready')
    def test_on_start_when_redis_is_ready(self, is_ready):
        # Given
        self.harness.set_leader(True)
        is_ready.return_value = True
        # When
        self.harness.charm.on.start.emit()
        # Then
        is_ready.assert_called_once_with()
        self.assertEqual(
            self.harness.charm.unit.status,
            ActiveStatus()
        )

    def test_on_stop(self):
        # When
        self.harness.charm.on.stop.emit()
        # Then
        self.assertEqual(
            self.harness.charm.unit.status,
            MaintenanceStatus('Pod is terminating.')
        )

    def test_on_config_changed_when_unit_is_not_leader(self):
        # Given
        self.harness.set_leader(False)
        # When
        self.harness.charm.on.config_changed.emit()
        # Then
        self.assertEqual(
            self.harness.charm.unit.status,
            ActiveStatus()
        )

    @mock.patch.object(RedisClient, 'is_ready')
    def test_on_config_changed_when_unit_is_leader_and_redis_is_ready(self, is_ready):
        # Given
        self.harness.set_leader(True)
        is_ready.return_value = True
        # When
        self.harness.charm.on.config_changed.emit()
        # Then
        self.assertEqual(
            self.harness.charm.unit.status,
            ActiveStatus()
        )

    @mock.patch.object(OCIImageResource, 'fetch')
    def test_on_config_changed_when_unit_is_leader_but_image_fetch_breaks(self, fetch):
        # Given
        self.harness.set_leader(True)
        fetch.side_effect = OCIImageResourceError("redis-image")
        # When
        self.harness.charm.on.config_changed.emit()
        # Then
        fetch.assert_called_once_with()
        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Error fetching image information.")
        )

    def test_on_update_status_when_unit_is_not_leader(self):
        # Given
        self.harness.set_leader(False)
        # When
        self.harness.charm.on.update_status.emit()
        # Then
        self.assertEqual(
            self.harness.charm.unit.status,
            ActiveStatus()
        )

    @mock.patch.object(RedisClient, 'is_ready')
    def test_on_update_status_when_redis_is_not_ready(self, is_ready):
        # Given
        self.harness.set_leader(True)
        is_ready.return_value = False
        # When
        self.harness.charm.on.update_status.emit()
        # Then
        is_ready.assert_called_once_with()
        self.assertEqual(
            self.harness.charm.unit.status,
            WaitingStatus("Waiting for Redis ...")
        )

    @mock.patch.object(RedisClient, 'is_ready')
    def test_on_update_status_when_redis_is_ready(self, is_ready):
        # Given
        self.harness.set_leader(True)
        is_ready.return_value = True
        # When
        self.harness.charm.on.update_status.emit()
        # Then
        is_ready.assert_called_once_with()
        self.assertEqual(
            self.harness.charm.unit.status,
            ActiveStatus()
        )

    @mock.patch.object(RedisProvides, '_bind_address')
    def test_on_relation_changed_status_when_unit_is_leader(self, bind_address):
        # Given
        self.harness.set_leader(True)
        bind_address.return_value = '10.2.1.5'

        rel_id = self.harness.add_relation('redis', 'wordpress')
        self.harness.add_relation_unit(rel_id, 'wordpress/0')
        # When
        self.harness.update_relation_data(rel_id, 'wordpress/0', {})
        rel_data = self.harness.get_relation_data(
            rel_id, self.harness.charm.unit.name
        )
        # Then
        self.assertEqual(rel_data.get('hostname'), '10.2.1.5')
        self.assertEqual(rel_data.get('port'), '6379')
