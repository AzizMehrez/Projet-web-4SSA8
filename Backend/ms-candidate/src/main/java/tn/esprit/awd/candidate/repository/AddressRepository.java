package tn.esprit.awd.candidate.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import tn.esprit.awd.candidate.entity.Address;

public interface AddressRepository extends JpaRepository<Address, Long> {
}
